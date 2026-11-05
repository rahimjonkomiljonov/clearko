"""NLLB worker process:  python -m app.explain.nllb_worker MODEL DEVICE

Runs in its own process because torch and PaddleOCR cannot share one process on Windows: both
load their own (different) cuDNN DLLs and the second import fails. Protocol: one JSON object per
line on stdin  {"code": "uzn_Latn", "sentences": [...]}  ->  one JSON line on stdout
{"sentences": [...]}  or  {"error": "..."}. Text is never written to stderr or any log.
"""

from __future__ import annotations

import json
import sys

MIN_FREE_GPU_BYTES = 3_500_000_000  # fp16 1.3B model + generation needs about 2.8 GB
SRC_CODE = "eng_Latn"


class NLLBModel:
    def __init__(self, model_name: str, device_setting: str = "auto", batch_size: int = 16):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.batch_size = batch_size
        self.device = self._pick_device(torch, device_setting)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tok = AutoTokenizer.from_pretrained(model_name, src_lang=SRC_CODE)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name, dtype=dtype)
        self.model.to(self.device).eval()

    @staticmethod
    def _pick_device(torch, setting: str) -> str:  # type: ignore[no-untyped-def]
        if setting == "cpu" or not torch.cuda.is_available():
            return "cpu"
        if setting == "auto":
            free, _ = torch.cuda.mem_get_info()
            if free < MIN_FREE_GPU_BYTES:  # e.g. the chat model is still loaded in video memory
                return "cpu"
        return "cuda"

    def translate(self, target_code: str, sentences: list[str]) -> list[str]:
        """Shortest sentences first inside each batch for less padding; order is restored."""
        import torch

        order = sorted(range(len(sentences)), key=lambda i: len(sentences[i]))
        result = [""] * len(sentences)
        for start in range(0, len(order), self.batch_size):
            idx = order[start : start + self.batch_size]
            enc = self.tok([sentences[i] for i in idx], return_tensors="pt", padding=True,
                           truncation=True, max_length=256).to(self.device)
            with torch.no_grad():
                ids = self.model.generate(
                    **enc,
                    forced_bos_token_id=self.tok.convert_tokens_to_ids(target_code),
                    num_beams=4,
                    max_length=None,
                    max_new_tokens=256,
                )
            for i, text in zip(idx, self.tok.batch_decode(ids, skip_special_tokens=True)):
                result[i] = text
        return result


def main() -> None:
    model_name = sys.argv[1]
    device = sys.argv[2] if len(sys.argv) > 2 else "auto"
    out = sys.stdout
    sys.stdout = sys.stderr  # stray prints from libraries must not corrupt the protocol
    model: NLLBModel | None = None
    for line in sys.stdin:
        try:
            req = json.loads(line)
            if model is None:
                model = NLLBModel(model_name, device)
            reply = {"sentences": model.translate(req["code"], req["sentences"])}
        except Exception as e:  # noqa: BLE001  report the type only: messages could echo text
            reply = {"error": type(e).__name__}
        out.write(json.dumps(reply, ensure_ascii=False) + "\n")
        out.flush()


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    main()
