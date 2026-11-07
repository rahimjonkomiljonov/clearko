"""User-facing error messages in the three app languages.

The Russian and Uzbek texts were written by hand (not machine translated) and still need a
native speaker's review before release.
"""

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "blurry": "The photo is too blurry. Hold the phone steady, use good light and retake it.",
        "no_text": "No text was found. Make sure the whole page is in the photo and try again.",
        "unsupported": "This does not look like a rental contract, phone plan or part-time job "
        "document.",
        "explain_failed": "Could not explain this document right now. Please try again in a minute.",
        "busy": "ClearKo is busy. Please try again in a few minutes.",
        "rate_limited": "Too many requests. Please try again later.",
        "bad_file": "This file could not be opened. Upload a JPG, PNG or PDF.",
        "heic": "iPhone HEIC photos are not supported. In the camera settings choose "
        "\"Most Compatible\" and take the photo again.",
        "too_large": "The file is too large. Take a smaller photo or fewer pages.",
        "too_many": "Too many pages. You can upload up to {n} pages at once.",
        "no_files": "Choose at least one photo or PDF.",
        "bad_lang": "Unknown language.",
        "bad_request": "Invalid request.",
        "not_found": "This result is no longer available. Please upload the document again.",
        "internal": "Something went wrong. Please try again.",
    },
    "ru": {
        "blurry": "Фото слишком размытое. Держите телефон ровно, включите хороший свет и "
        "сфотографируйте снова.",
        "no_text": "Текст не найден. Убедитесь, что вся страница в кадре, и попробуйте ещё раз.",
        "unsupported": "Это не похоже на договор аренды, договор мобильного тарифа или трудовой "
        "договор на подработку.",
        "explain_failed": "Сейчас не удалось разобрать этот документ. Попробуйте ещё раз через "
        "минуту.",
        "busy": "ClearKo сейчас занят. Попробуйте через несколько минут.",
        "rate_limited": "Слишком много запросов. Попробуйте позже.",
        "bad_file": "Не удалось открыть файл. Загрузите JPG, PNG или PDF.",
        "heic": "Фото iPhone в формате HEIC не поддерживаются. В настройках камеры выберите "
        "«Наиболее совместимый» и сфотографируйте снова.",
        "too_large": "Файл слишком большой. Сделайте фото поменьше или загрузите меньше страниц.",
        "too_many": "Слишком много страниц. За раз можно загрузить до {n} страниц.",
        "no_files": "Выберите хотя бы одно фото или PDF.",
        "bad_lang": "Неизвестный язык.",
        "bad_request": "Некорректный запрос.",
        "not_found": "Этот результат больше недоступен. Загрузите документ ещё раз.",
        "internal": "Что-то пошло не так. Попробуйте ещё раз.",
    },
    "uz": {
        "blurry": "Rasm juda xira. Telefonni qimirlatmasdan ushlang, yorug'lik yaxshi bo'lsin va "
        "qaytadan suratga oling.",
        "no_text": "Matn topilmadi. Butun sahifa suratga tushganiga ishonch hosil qiling va qayta "
        "urinib ko'ring.",
        "unsupported": "Bu ijara shartnomasi, telefon tarifi yoki qisman bandlik (part-time) "
        "shartnomasiga o'xshamaydi.",
        "explain_failed": "Hozir bu hujjatni tushuntirib bo'lmadi. Bir daqiqadan keyin qayta "
        "urinib ko'ring.",
        "busy": "ClearKo hozir band. Bir necha daqiqadan keyin qayta urinib ko'ring.",
        "rate_limited": "So'rovlar juda ko'p. Keyinroq qayta urinib ko'ring.",
        "bad_file": "Faylni ochib bo'lmadi. JPG, PNG yoki PDF yuklang.",
        "heic": "iPhone HEIC rasmlari qo'llab-quvvatlanmaydi. Kamera sozlamalarida "
        "\"Most Compatible\" ni tanlang va qaytadan suratga oling.",
        "too_large": "Fayl juda katta. Kichikroq rasm oling yoki kamroq sahifa yuklang.",
        "too_many": "Sahifalar juda ko'p. Bir vaqtda {n} tagacha sahifa yuklash mumkin.",
        "no_files": "Kamida bitta rasm yoki PDF tanlang.",
        "bad_lang": "Noma'lum til.",
        "bad_request": "Noto'g'ri so'rov.",
        "not_found": "Bu natija endi mavjud emas. Hujjatni qaytadan yuklang.",
        "internal": "Nimadir xato ketdi. Qayta urinib ko'ring.",
    },
}


def message(code: str, lang: str = "en", **fmt: object) -> str:
    table = MESSAGES.get(lang, MESSAGES["en"])
    return table.get(code, MESSAGES["en"][code]).format(**fmt)
