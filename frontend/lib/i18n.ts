// UI texts. The Russian and Uzbek texts were written by hand (not machine translated)
// and still need a native speaker's review.
import type { DocType, Lang, Severity } from "./types";
import type { StepKey } from "./progress";

export interface Texts {
  tagline: string;
  disclaimerShort: string;
  language: string;
  docTypeLabel: string;
  docTypes: Record<"auto" | DocType, string>;
  addPhoto: string;
  takePhoto: string;
  choosePhoto: string;
  pagesAdded: (n: number) => string;
  addMore: string;
  remove: string;
  tipText: string;
  analyze: string;
  uploading: string;
  working: string;
  waitHint: string;
  steps: Record<StepKey, string>;
  cancel: string;
  summary: string;
  keyFacts: string;
  redFlags: string;
  noRedFlags: string;
  todos: string;
  deadline: string;
  original: string;
  severity: Record<Severity, string>;
  unverifiedNumber: string;
  warnings: string;
  deleteResult: string;
  deleted: string;
  newDocument: string;
  tryAgain: string;
  retryIn: (s: number) => string;
  privacy: string;
  privacyLink: string;
  privacyTitle: string;
  privacyPoints: string[];
  privacyLocal: string;
  privacyCloud: string;
  back: string;
  errors: Record<string, string>;
}

const en: Texts = {
  tagline: "Understand any Korean document",
  disclaimerShort: "ClearKo explains documents. It is not legal advice.",
  language: "Language",
  docTypeLabel: "Type of document",
  docTypes: {
    auto: "Detect automatically",
    rental: "Rental contract",
    phone_plan: "Phone plan",
    part_time: "Part-time job contract",
  },
  addPhoto: "Add photos of the document",
  takePhoto: "Take a photo",
  choosePhoto: "Choose from gallery or files",
  pagesAdded: (n) => (n === 1 ? "1 page added" : `${n} pages added`),
  addMore: "Add another page",
  remove: "Remove",
  tipText: "Put the page flat in good light, fill the frame, keep it sharp. One photo per page, in order.",
  analyze: "Explain this document",
  uploading: "Uploading…",
  working: "Reading your document",
  waitHint: "This takes 1–2 minutes. Please keep this page open.",
  steps: {
    queued: "Waiting for a free slot",
    reading: "Reading the pages",
    summarizing: "Summarizing",
    reviewing: "Checking every clause",
    translating: "Translating",
    done: "Done",
  },
  cancel: "Cancel",
  summary: "Summary",
  keyFacts: "Key facts",
  redFlags: "Things to watch out for",
  noRedFlags: "No red flags found. This does not mean the document is safe: read it yourself too.",
  todos: "What to do",
  deadline: "By",
  original: "Original text",
  severity: { high: "Serious", medium: "Check", low: "Minor" },
  unverifiedNumber: "A number here could not be matched to the scan. Check it in the original.",
  warnings: "Notes",
  deleteResult: "Delete this result",
  deleted: "Result deleted. Nothing is stored.",
  newDocument: "Explain another document",
  tryAgain: "Try again",
  retryIn: (s) => `Try again in about ${Math.ceil(s / 60)} min.`,
  privacy:
    "Your photos are read in memory and deleted when the analysis ends. Results are kept for 15 minutes at most.",
  privacyLink: "Privacy",
  privacyTitle: "Privacy",
  privacyPoints: [
    "Your photos are decoded in the server's memory, read, and dropped as soon as the analysis ends. They are never written to disk by ClearKo.",
    "The result is kept in memory for 15 minutes at most, then deleted. \"Delete this result\" removes it at once. Closing the page also asks the server to delete it.",
    "ClearKo has no accounts, no database and no analytics, and does not log the text of your documents. Logs hold only technical data (a short job id, error codes, timings).",
    "Your browser remembers only your language choice. The app is installable but caches nothing about your documents.",
    "Do not upload documents of other people without their permission. Hide your ID number if you can.",
    "ClearKo explains documents. It is not legal advice. Check important points with the other party, a lawyer, or an official counter.",
  ],
  privacyLocal: "On this server the text is processed by a model that runs on the server itself. It is not sent to any other company.",
  privacyCloud: "On this server the text of your document is sent to a cloud AI service to write the explanation. Do not upload anything you are not comfortable sharing.",
  back: "Back",
  errors: {
    network: "Cannot reach the server. Check your connection and try again.",
    heic: "iPhone HEIC photos are not supported. Choose a JPG or PNG, or take the photo with the in-app camera.",
    bad_file: "This file could not be read. Use a JPG, PNG, WebP or PDF.",
    too_large: "The files are too big. Use fewer or smaller photos.",
    no_files: "Add at least one photo first.",
    too_many: "Too many pages. Send fewer photos.",
    rate_limited: "You have used the limit for now. Please try again later.",
    busy: "ClearKo is busy right now. Please try again in a minute.",
    blurry: "The photo is too blurry. Take it again, holding the phone steady in good light.",
    no_text: "No text was found in the photo. Make sure the document fills the frame.",
    unsupported: "This does not look like a rental, phone plan or part-time job document.",
    explain_failed: "The explanation failed. Please try again.",
    not_found: "This result has expired. Please upload the document again.",
    internal: "Something went wrong. Please try again.",
  },
};

const ru: Texts = {
  tagline: "Поймите любой корейский документ",
  disclaimerShort: "ClearKo объясняет документы. Это не юридическая консультация.",
  language: "Язык",
  docTypeLabel: "Тип документа",
  docTypes: {
    auto: "Определить автоматически",
    rental: "Договор аренды жилья",
    phone_plan: "Тариф мобильной связи",
    part_time: "Договор подработки",
  },
  addPhoto: "Добавьте фото документа",
  takePhoto: "Сделать фото",
  choosePhoto: "Выбрать из галереи или файлов",
  pagesAdded: (n) => `Добавлено страниц: ${n}`,
  addMore: "Добавить ещё страницу",
  remove: "Убрать",
  tipText: "Положите страницу ровно при хорошем свете, чтобы она занимала весь кадр и была чёткой. Одно фото на страницу, по порядку.",
  analyze: "Объяснить документ",
  uploading: "Загрузка…",
  working: "Читаем ваш документ",
  waitHint: "Это займёт 1–2 минуты. Не закрывайте страницу.",
  steps: {
    queued: "Ждём свободного места",
    reading: "Читаем страницы",
    summarizing: "Составляем краткое содержание",
    reviewing: "Проверяем каждый пункт",
    translating: "Переводим",
    done: "Готово",
  },
  cancel: "Отмена",
  summary: "Кратко",
  keyFacts: "Главное",
  redFlags: "На что обратить внимание",
  noRedFlags: "Тревожных пунктов не найдено. Это не значит, что документ безопасен: прочитайте его и сами.",
  todos: "Что делать",
  deadline: "До",
  original: "Исходный текст",
  severity: { high: "Серьёзно", medium: "Проверьте", low: "Мелочь" },
  unverifiedNumber: "Это число не удалось сверить со сканом. Проверьте его в оригинале.",
  warnings: "Примечания",
  deleteResult: "Удалить результат",
  deleted: "Результат удалён. Ничего не хранится.",
  newDocument: "Объяснить другой документ",
  tryAgain: "Повторить",
  retryIn: (s) => `Повторите примерно через ${Math.ceil(s / 60)} мин.`,
  privacy:
    "Ваши фото обрабатываются в памяти и удаляются после анализа. Результат хранится не дольше 15 минут.",
  privacyLink: "Конфиденциальность",
  privacyTitle: "Конфиденциальность",
  privacyPoints: [
    "Ваши фото расшифровываются в памяти сервера, читаются и удаляются сразу после анализа. ClearKo никогда не записывает их на диск.",
    "Результат хранится в памяти не дольше 15 минут и затем удаляется. Кнопка «Удалить результат» стирает его сразу. При закрытии страницы сервер тоже получает просьбу удалить результат.",
    "В ClearKo нет аккаунтов, базы данных и аналитики, текст ваших документов не записывается в журналы. В журналах только технические данные (короткий номер задания, коды ошибок, время).",
    "Браузер запоминает только выбранный вами язык. Приложение можно установить, но оно ничего не сохраняет о ваших документах.",
    "Не загружайте чужие документы без разрешения владельца. Закройте номер удостоверения, если можете.",
    "ClearKo объясняет документы. Это не юридическая консультация. Важные моменты проверяйте у другой стороны, юриста или в официальной службе.",
  ],
  privacyLocal: "На этом сервере текст обрабатывает модель, работающая на самом сервере. Он не отправляется другим компаниям.",
  privacyCloud: "На этом сервере текст вашего документа отправляется в облачный ИИ-сервис для составления объяснения. Не загружайте то, чем не готовы поделиться.",
  back: "Назад",
  errors: {
    network: "Нет связи с сервером. Проверьте интернет и повторите.",
    heic: "Фото iPhone в формате HEIC не поддерживаются. Выберите JPG или PNG либо снимите фото через камеру в приложении.",
    bad_file: "Не удалось прочитать файл. Используйте JPG, PNG, WebP или PDF.",
    too_large: "Файлы слишком большие. Отправьте меньше или меньшего размера фото.",
    no_files: "Сначала добавьте хотя бы одно фото.",
    too_many: "Слишком много страниц. Отправьте меньше фото.",
    rate_limited: "Лимит на сейчас исчерпан. Попробуйте позже.",
    busy: "ClearKo сейчас занят. Повторите через минуту.",
    blurry: "Фото слишком размытое. Снимите ещё раз, держа телефон неподвижно при хорошем свете.",
    no_text: "На фото не найден текст. Документ должен занимать весь кадр.",
    unsupported: "Это не похоже на договор аренды, тариф связи или договор подработки.",
    explain_failed: "Не удалось составить объяснение. Попробуйте ещё раз.",
    not_found: "Результат устарел. Загрузите документ заново.",
    internal: "Что-то пошло не так. Попробуйте ещё раз.",
  },
};

const uz: Texts = {
  tagline: "Har qanday koreyscha hujjatni tushuning",
  disclaimerShort: "ClearKo hujjatlarni tushuntiradi. Bu yuridik maslahat emas.",
  language: "Til",
  docTypeLabel: "Hujjat turi",
  docTypes: {
    auto: "Avtomatik aniqlash",
    rental: "Uy ijarasi shartnomasi",
    phone_plan: "Mobil aloqa tarifi",
    part_time: "Yarim kunlik ish shartnomasi",
  },
  addPhoto: "Hujjat suratlarini qo‘shing",
  takePhoto: "Suratga olish",
  choosePhoto: "Galereya yoki fayllardan tanlash",
  pagesAdded: (n) => `Qo‘shilgan sahifalar: ${n}`,
  addMore: "Yana sahifa qo‘shish",
  remove: "Olib tashlash",
  tipText: "Sahifani tekis, yaxshi yorug‘likda qo‘ying, kadrni to‘ldirsin va aniq bo‘lsin. Har sahifaga bitta surat, tartib bilan.",
  analyze: "Hujjatni tushuntirish",
  uploading: "Yuklanmoqda…",
  working: "Hujjatingiz o‘qilmoqda",
  waitHint: "Bu 1–2 daqiqa oladi. Sahifani yopmang.",
  steps: {
    queued: "Navbat kutilmoqda",
    reading: "Sahifalar o‘qilmoqda",
    summarizing: "Qisqacha mazmun tuzilmoqda",
    reviewing: "Har bir band tekshirilmoqda",
    translating: "Tarjima qilinmoqda",
    done: "Tayyor",
  },
  cancel: "Bekor qilish",
  summary: "Qisqacha",
  keyFacts: "Asosiy ma’lumotlar",
  redFlags: "E’tibor bering",
  noRedFlags: "Xavfli bandlar topilmadi. Bu hujjat xavfsiz degani emas: o‘zingiz ham o‘qib chiqing.",
  todos: "Nima qilish kerak",
  deadline: "Muddat",
  original: "Asl matn",
  severity: { high: "Jiddiy", medium: "Tekshiring", low: "Arzimas" },
  unverifiedNumber: "Bu raqamni skan bilan solishtirib bo‘lmadi. Asl nusxadan tekshiring.",
  warnings: "Izohlar",
  deleteResult: "Natijani o‘chirish",
  deleted: "Natija o‘chirildi. Hech narsa saqlanmaydi.",
  newDocument: "Boshqa hujjatni tushuntirish",
  tryAgain: "Qayta urinish",
  retryIn: (s) => `Taxminan ${Math.ceil(s / 60)} daqiqadan keyin qayta urining.`,
  privacy:
    "Suratlaringiz xotirada o‘qiladi va tahlil tugagach o‘chiriladi. Natija ko‘pi bilan 15 daqiqa saqlanadi.",
  privacyLink: "Maxfiylik",
  privacyTitle: "Maxfiylik",
  privacyPoints: [
    "Suratlaringiz server xotirasida ochiladi, o‘qiladi va tahlil tugashi bilan o‘chiriladi. ClearKo ularni hech qachon diskka yozmaydi.",
    "Natija xotirada ko‘pi bilan 15 daqiqa saqlanadi, so‘ng o‘chiriladi. «Natijani o‘chirish» tugmasi uni darhol o‘chiradi. Sahifani yopsangiz ham, serverdan uni o‘chirish so‘raladi.",
    "ClearKo’da akkaunt, ma’lumotlar bazasi va analitika yo‘q, hujjatlaringiz matni jurnalga yozilmaydi. Jurnalda faqat texnik ma’lumot bor (qisqa vazifa raqami, xato kodlari, vaqt).",
    "Brauzer faqat tanlagan tilingizni eslab qoladi. Ilovani o‘rnatish mumkin, lekin u hujjatlaringiz haqida hech narsa saqlamaydi.",
    "Boshqa odamlarning hujjatlarini ularning ruxsatisiz yuklamang. Imkon bo‘lsa, guvohnoma raqamini yoping.",
    "ClearKo hujjatlarni tushuntiradi. Bu yuridik maslahat emas. Muhim jihatlarni boshqa tomon, advokat yoki rasmiy idora bilan tekshiring.",
  ],
  privacyLocal: "Bu serverda matnni serverning o‘zida ishlaydigan model qayta ishlaydi. U boshqa kompaniyaga yuborilmaydi.",
  privacyCloud: "Bu serverda hujjatingiz matni tushuntirish yozish uchun bulutli sun’iy intellekt xizmatiga yuboriladi. Ulashishga tayyor bo‘lmagan narsani yuklamang.",
  back: "Orqaga",
  errors: {
    network: "Serverga ulanib bo‘lmadi. Internetni tekshirib, qayta urining.",
    heic: "iPhone HEIC suratlari qo‘llab-quvvatlanmaydi. JPG yoki PNG tanlang yoki ilovadagi kamera bilan suratga oling.",
    bad_file: "Faylni o‘qib bo‘lmadi. JPG, PNG, WebP yoki PDF ishlating.",
    too_large: "Fayllar juda katta. Kamroq yoki kichikroq suratlar yuboring.",
    no_files: "Avval kamida bitta surat qo‘shing.",
    too_many: "Sahifalar juda ko‘p. Kamroq surat yuboring.",
    rate_limited: "Hozircha limit tugadi. Keyinroq urinib ko‘ring.",
    busy: "ClearKo hozir band. Bir daqiqadan keyin qayta urining.",
    blurry: "Surat juda xira. Telefonni qimirlatmay, yaxshi yorug‘likda qayta oling.",
    no_text: "Suratda matn topilmadi. Hujjat kadrni to‘ldirishi kerak.",
    unsupported: "Bu ijara, mobil tarif yoki yarim kunlik ish hujjatiga o‘xshamaydi.",
    explain_failed: "Tushuntirish tayyorlanmadi. Qayta urinib ko‘ring.",
    not_found: "Natija eskirgan. Hujjatni qaytadan yuklang.",
    internal: "Nimadir xato ketdi. Qayta urinib ko‘ring.",
  },
};

export const TEXTS: Record<Lang, Texts> = { en, ru, uz };

export const LANG_NAMES: Record<Lang, string> = { uz: "O‘zbekcha", ru: "Русский", en: "English" };

/** Best first guess for a new visitor, from the browser language. */
export function guessLang(browserLangs: readonly string[]): Lang {
  for (const l of browserLangs) {
    const code = l.toLowerCase().slice(0, 2);
    if (code === "uz" || code === "ru" || code === "en") return code;
  }
  return "en";
}

/** The API's own message wins (it is already in the right language); else our text for the code. */
export function errorText(t: Texts, code: string, apiMessage: string): string {
  return apiMessage || t.errors[code] || t.errors.internal;
}
