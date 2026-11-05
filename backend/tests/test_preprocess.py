import cv2
import numpy as np
import pytest

from app.preprocess import BlurryImageError, ImageDecodeError, decode_image, preprocess, steps


def make_text_page(width=900, height=1200, lines=14) -> np.ndarray:
    """White page with horizontal lines of dense dark 'text' (Latin, just for geometry)."""
    img = np.full((height, width, 3), 255, np.uint8)
    for i in range(lines):
        y = 120 + i * 65
        cv2.putText(img, "ABCDEFG HIJKLMN OPQRSTU 12345 67890", (60, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3, cv2.LINE_AA)
    return img


def test_decode_rejects_garbage():
    with pytest.raises(ImageDecodeError):
        decode_image(b"not an image")


def test_decode_roundtrip():
    ok, buf = cv2.imencode(".png", make_text_page())
    assert ok
    assert decode_image(buf.tobytes()).shape == (1200, 900, 3)


def test_blur_score_sharp_vs_blurred():
    sharp = make_text_page()
    blurred = cv2.GaussianBlur(sharp, (31, 31), 0)
    assert steps.blur_score(sharp) > 10 * steps.blur_score(blurred)


def test_pipeline_rejects_blurry():
    blurred = cv2.GaussianBlur(make_text_page(), (41, 41), 0)
    with pytest.raises(BlurryImageError):
        preprocess(blurred, blur_threshold=60.0)


def test_skew_estimate_recovers_angle():
    page = make_text_page()
    h, w = page.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 6.0, 1.0)  # rotate CCW 6 degrees
    skewed = cv2.warpAffine(page, m, (w, h), borderValue=(255, 255, 255))
    est = steps.estimate_skew_angle(skewed)
    # Correcting rotation must be the inverse of the applied one.
    assert abs(abs(est) - 6.0) < 1.5
    fixed = steps.rotate(skewed, est)
    assert abs(steps.estimate_skew_angle(fixed)) < 1.5


def test_skew_of_straight_page_is_small():
    assert abs(steps.estimate_skew_angle(make_text_page())) < 1.0


def test_perspective_crop_finds_page_on_dark_background():
    page = make_text_page(600, 800)
    canvas = np.full((1000, 1000, 3), 40, np.uint8)
    src = np.float32([[0, 0], [599, 0], [599, 799], [0, 799]])
    dst = np.float32([[180, 90], [800, 130], [770, 900], [140, 850]])
    m = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(page, m, (1000, 1000), dst=canvas, borderMode=cv2.BORDER_TRANSPARENT)
    quad = steps.find_document_quad(warped)
    assert quad is not None
    # Each detected corner should be near one of the true corners.
    for corner in dst:
        assert min(np.linalg.norm(quad - corner, axis=1)) < 25
    cropped = steps.perspective_crop(warped, quad)
    assert 500 < cropped.shape[1] < 750 and 700 < cropped.shape[0] < 950


def test_no_quad_on_blank_dark_image():
    assert steps.find_document_quad(np.full((400, 400, 3), 30, np.uint8)) is None


def test_resize_only_shrinks():
    big = np.zeros((4000, 2000, 3), np.uint8)
    assert max(steps.resize_max_side(big, 2400).shape[:2]) == 2400
    small = np.zeros((500, 300, 3), np.uint8)
    assert steps.resize_max_side(small, 2400) is small


def test_default_pipeline_is_conservative():
    result = preprocess(make_text_page())
    assert "perspective_crop" not in result.applied and "contrast" not in result.applied
    assert result.image.ndim == 3


def test_optional_steps_can_be_enabled():
    result = preprocess(make_text_page(), crop=True, contrast=True)
    assert "contrast" in result.applied
