/**
 * Three languages: Arabic (default, right to left), French, English.
 *
 * Two rules this file exists to enforce:
 *
 * 1. No user-facing string is written anywhere else. If a component needs
 *    words, it needs a key here.
 * 2. The API returns error *codes*, never sentences. `errors.<code>` is where
 *    a code becomes something a person can read, which is why adding a code on
 *    the server means adding three lines here.
 *
 * Numbers, prices, phone numbers and references stay Latin and left to right in
 * all three — see `src/lib/format.ts`. Sentences are never built by
 * concatenation; interpolation only, because word order is not the same in the
 * three languages.
 */

import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'

export const LANGUAGES = ['ar', 'fr', 'en'] as const
export type Language = (typeof LANGUAGES)[number]

export const DEFAULT_LANGUAGE: Language = 'ar'
const RTL_LANGUAGES: readonly Language[] = ['ar']
const STORAGE_KEY = 'brikole.language'

export const LANGUAGE_LABELS: Record<Language, string> = {
  ar: 'العربية',
  fr: 'Français',
  en: 'English',
}

const ar = {
  common: {
    appName: 'بريكول',
    loading: 'جاري التحميل…',
    retry: 'حاول مرة أخرى',
    cancel: 'إلغاء',
    confirm: 'تأكيد',
    save: 'حفظ',
    back: 'رجوع',
    next: 'التالي',
    search: 'بحث',
    close: 'إغلاق',
    optional: 'اختياري',
    signIn: 'تسجيل الدخول',
    signOut: 'تسجيل الخروج',
    signUp: 'إنشاء حساب',
    language: 'اللغة',
    theme: 'المظهر',
    themeLight: 'فاتح',
    themeDark: 'داكن',
    themeSystem: 'حسب النظام',
  },
  provider: {
    topRated: 'مطلوب بزاف',
    newHere: 'جديد هنا',
    jobsDone: '{{count}} خدمة',
    startingAt: 'ابتداء من',
    onQuote: 'الثمن حسب الخدمة',
  },
  roles: {
    client: 'زبون',
    provider: 'معلّم',
    moderator: 'مشرف',
    admin: 'مدير',
  },
  landing: {
    title: 'لقا المعلّم اللي محتاج، بسرعة',
    subtitle: 'سباك، كهربائي، صباغ، نجار… وصف الخدمة وتوصلك عروض بالثمن.',
    ctaClient: 'اطلب خدمة',
    ctaProvider: 'ولّي معلّم عندنا',
    searchPlaceholder: 'شنو محتاج؟',
    searchCta: 'قلّب',
    popular: 'مطلوبين بزاف',
    city: 'المدينة',
    cityAll: 'كل المدن',
    providersOne: 'معلّم واحد',
    providersMany: '{{count}} معلّم',
    noProviderHere: 'مازال حتى واحد هنا',
    countsInCity: 'فـ {{city}}',
    countsEverywhere: 'فالمغرب كامل',
    trustNote: 'بلا عمولة على ثمن الخدمة · الخلاص نقداً مباشرة للمعلّم',
    topProviders: 'أحسن المعلّمين',
    seeAll: 'شوف الكل',
    noProviders: 'ما كاين حتى معلّم فهاد المدينة',
    browseByTrade: 'قلّب حسب الحرفة',
    tradesTitle: 'الحرف',
    tradesEmpty: 'ما كاين حتى حرفة دابا',
    howTitle: 'كيفاش كيخدم',
    how1Title: 'وصف الخدمة',
    how1Body: 'شنو محتاج، فين، وإمتى. زيد تصاور إلى بغيتي.',
    how2Title: 'توصلك عروض',
    how2Body: 'المعلّمين اللي فحرفتك وفمدينتك كيصيفطو ليك الثمن ديالهم.',
    how3Title: 'اختار وخلّص نقداً',
    how3Body: 'كتختار اللي عجبك، وكتخلّص المعلّم مباشرة. المنصة ما كتمسّش الفلوس.',
    forProsTitle: 'واش نتا معلّم؟',
    forProsBody: 'توصلك طلبات من الزبناء فمدينتك. ما كاين لا عمولة على ثمن الخدمة ولا اشتراك — كتخلّص غير منين العرض ديالك يتقبل.',
  },
  auth: {
    phone: 'رقم الهاتف',
    phoneHint: 'الرقم اللي كيتواصلو بيه معاك',
    fullName: 'الاسم الكامل',
    password: 'كلمة السر',
    passwordHint: '8 حروف على الأقل، فيهم حرف ورقم',
    currentPassword: 'كلمة السر الحالية',
    newPassword: 'كلمة السر الجديدة',
    loginTitle: 'مرحباً بك من جديد',
    loginSubtitle: 'دخل لحسابك باش تكمّل.',
    registerSubtitle: 'دقيقة وحدة و تكون واجد.',
    show: 'بيّن',
    hide: 'خبّي',
    promise1: 'عروض بالثمن، غالباً فسوايع.',
    promise2: 'تنقيط حقيقي من زبناء حقيقيين.',
    promise3: 'كتخلّص المعلّم نقداً منين تسالى الخدمة.',
    loginCta: 'دخول',
    noAccount: 'ما عندكش حساب؟',
    haveAccount: 'عندك حساب؟',
    registerTitle: 'إنشاء حساب',
    registerCta: 'إنشاء الحساب',
    chooseRole: 'شنو بغيتي دير؟',
    roleClientTitle: 'محتاج خدمة',
    roleClientBody: 'كتوصف الخدمة وكتوصلك عروض.',
    roleProviderTitle: 'أنا معلّم',
    roleProviderBody: 'كتوصلك طلبات وكتصيفط عروضك.',
    roleLockedNote: 'النوع ديال الحساب ما كيتبدّلش من بعد إلا عن طريق المدير.',
    forgot: 'نسيتي كلمة السر؟',
    forgotBody: 'دابا التواصل مع المدير هو الطريقة الوحيدة لإعادة تعيينها. إعادة التعيين برسالة SMS غادي تجي من بعد.',
  },
  errors: {
    generic: 'وقع خطأ. عاود المحاولة.',
    network: 'ما قدرناش نتواصلو مع الخادم. تحقق من الاتصال.',
    phone_invalid: 'هاد الرقم ماشي صحيح. مثال: 0612345678',
    password_too_weak: 'كلمة السر خاصها 8 حروف على الأقل، فيهم حرف ورقم.',
    validation_failed: 'كاين شي معلومة ناقصة ولا ماشي صحيحة.',
    phone_taken: 'هاد الرقم عندو حساب من قبل.',
    invalid_credentials: 'الرقم ولا كلمة السر ماشي صحيحين.',
    account_locked: 'الحساب مسدود مؤقتاً. عاود من بعد {{minutes}} دقيقة.',
    account_suspended: 'هاد الحساب موقوف.',
    role_not_self_registerable: 'هاد النوع ديال الحساب كيتصاوب غير من طرف المدير.',
    not_authenticated: 'خاصك تسجل الدخول.',
    forbidden: 'ما عندكش الصلاحية لهاد الصفحة.',
    token_expired: 'الجلسة سالات. سجل الدخول من جديد.',
    token_invalid: 'الجلسة ماشي صالحة. سجل الدخول من جديد.',
    token_wrong_type: 'الجلسة ماشي صالحة. سجل الدخول من جديد.',
    not_found: 'ما لقيناش هاد الشي.',
    conflict: 'هاد العملية تدارت من قبل.',
    insufficient_credit: 'الرصيد ما كافيش.',
    amount_invalid: 'هاد المبلغ ماشي صحيح.',
  },
  nav: {
    newRequest: 'طلب جديد',
    myRequests: 'الطلبات ديالي',
    requests: 'الطلبات',
    myOffers: 'العروض ديالي',
    myJobs: 'الخدمات ديالي',
    credit: 'الرصيد',
    notifications: 'الإشعارات',
    account: 'الحساب',
    disputes: 'النزاعات',
    reports: 'البلاغات',
    dashboard: 'لوحة القيادة',
    approvals: 'الموافقات',
    users: 'المستخدمين',
    finance: 'المالية',
    catalog: 'الحرف والمدن',
    settings: 'الإعدادات',
    audit: 'سجل العمليات',
  },
  notBuilt: {
    title: 'هاد الشاشة مازال ما تبناتش',
    body: 'الشاشة {{screen}} مبرمجة فـ docs/SCREENS.md وغادي تجي فالمرحلة الجاية.',
  },
  notFound: {
    title: 'ما لقيناش هاد الصفحة',
    cta: 'ارجع للرئيسية',
  },
  forbidden: {
    title: 'هاد الصفحة ماشي ديالك',
    body: 'الحساب ديالك ({{role}}) ما عندوش الصلاحية هنا.',
    cta: 'ارجع لصفحتك',
  },
} as const

const fr = {
  common: {
    appName: 'Brikole',
    loading: 'Chargement…',
    retry: 'Réessayer',
    cancel: 'Annuler',
    confirm: 'Confirmer',
    save: 'Enregistrer',
    back: 'Retour',
    next: 'Suivant',
    search: 'Rechercher',
    close: 'Fermer',
    optional: 'facultatif',
    signIn: 'Se connecter',
    signOut: 'Se déconnecter',
    signUp: 'Créer un compte',
    language: 'Langue',
    theme: 'Apparence',
    themeLight: 'Clair',
    themeDark: 'Sombre',
    themeSystem: 'Système',
  },
  provider: {
    topRated: 'Très demandé',
    newHere: 'Nouveau',
    jobsDone: '{{count}} travaux',
    startingAt: 'à partir de',
    onQuote: 'Sur devis',
  },
  roles: {
    client: 'Client',
    provider: 'M3allem',
    moderator: 'Modérateur',
    admin: 'Administrateur',
  },
  landing: {
    title: 'Trouvez le bon m3allem, rapidement',
    subtitle: 'Plombier, électricien, peintre, menuisier… Décrivez le travail, recevez des offres chiffrées.',
    ctaClient: 'Demander un service',
    ctaProvider: 'Devenir m3allem',
    searchPlaceholder: 'Quel service ?',
    searchCta: 'Chercher',
    popular: 'Les plus demandés',
    city: 'Ville',
    cityAll: 'Toutes les villes',
    providersOne: '1 m3allem',
    providersMany: '{{count}} m3allems',
    noProviderHere: 'Personne pour l’instant',
    countsInCity: 'à {{city}}',
    countsEverywhere: 'dans tout le Maroc',
    trustNote: 'Aucune commission sur le prix · Paiement en espèces, directement au m3allem',
    topProviders: 'Les m3allems les mieux notés',
    seeAll: 'Voir tout',
    noProviders: 'Aucun m3allem dans cette ville pour l’instant',
    browseByTrade: 'Parcourir par métier',
    tradesTitle: 'Les métiers',
    tradesEmpty: 'Aucun métier pour le moment',
    howTitle: 'Comment ça marche',
    how1Title: 'Décrivez le travail',
    how1Body: 'Ce qu’il faut faire, où, et quand. Ajoutez des photos si vous voulez.',
    how2Title: 'Recevez des offres',
    how2Body: 'Les m3allems de votre métier et de votre ville vous envoient leur prix.',
    how3Title: 'Choisissez et payez en espèces',
    how3Body: 'Vous choisissez, puis vous payez le m3allem directement. La plateforme ne touche pas à l’argent.',
    forProsTitle: 'Vous êtes m3allem ?',
    forProsBody: 'Recevez les demandes des clients de votre ville. Aucune commission sur le prix du travail, aucun abonnement — vous payez seulement quand votre offre est acceptée.',
  },
  auth: {
    phone: 'Numéro de téléphone',
    phoneHint: 'Le numéro sur lequel on vous joint',
    fullName: 'Nom complet',
    password: 'Mot de passe',
    passwordHint: '8 caractères minimum, avec une lettre et un chiffre',
    currentPassword: 'Mot de passe actuel',
    newPassword: 'Nouveau mot de passe',
    loginTitle: 'Content de vous revoir',
    loginSubtitle: 'Connectez-vous pour continuer.',
    registerSubtitle: 'Une minute, et c’est fait.',
    show: 'Afficher',
    hide: 'Masquer',
    promise1: 'Des offres chiffrées, souvent en quelques heures.',
    promise2: 'Des avis réels, de vrais clients.',
    promise3: 'Vous payez le m3allem en espèces, une fois le travail fait.',
    loginCta: 'Se connecter',
    noAccount: 'Pas encore de compte ?',
    haveAccount: 'Déjà un compte ?',
    registerTitle: 'Créer un compte',
    registerCta: 'Créer le compte',
    chooseRole: 'Vous venez pour…',
    roleClientTitle: 'J’ai besoin d’un service',
    roleClientBody: 'Vous décrivez le travail, vous recevez des offres.',
    roleProviderTitle: 'Je suis m3allem',
    roleProviderBody: 'Vous recevez des demandes et vous envoyez vos offres.',
    roleLockedNote: 'Le type de compte ne peut plus être changé ensuite, sauf par un administrateur.',
    forgot: 'Mot de passe oublié ?',
    forgotBody: 'Pour l’instant, un administrateur doit le réinitialiser. La réinitialisation par SMS arrivera plus tard.',
  },
  errors: {
    generic: 'Une erreur est survenue. Réessayez.',
    network: 'Impossible de joindre le serveur. Vérifiez votre connexion.',
    phone_invalid: 'Ce numéro n’est pas valide. Exemple : 0612345678',
    password_too_weak: 'Le mot de passe doit faire 8 caractères minimum, avec une lettre et un chiffre.',
    validation_failed: 'Une information est manquante ou incorrecte.',
    phone_taken: 'Ce numéro a déjà un compte.',
    invalid_credentials: 'Numéro ou mot de passe incorrect.',
    account_locked: 'Compte bloqué temporairement. Réessayez dans {{minutes}} minutes.',
    account_suspended: 'Ce compte est suspendu.',
    role_not_self_registerable: 'Ce type de compte est créé par un administrateur.',
    not_authenticated: 'Vous devez vous connecter.',
    forbidden: 'Vous n’avez pas accès à cette page.',
    token_expired: 'Session expirée. Reconnectez-vous.',
    token_invalid: 'Session invalide. Reconnectez-vous.',
    token_wrong_type: 'Session invalide. Reconnectez-vous.',
    not_found: 'Introuvable.',
    conflict: 'Cette opération a déjà été effectuée.',
    insufficient_credit: 'Solde insuffisant.',
    amount_invalid: 'Ce montant n’est pas valide.',
  },
  nav: {
    newRequest: 'Nouvelle demande',
    myRequests: 'Mes demandes',
    requests: 'Demandes',
    myOffers: 'Mes offres',
    myJobs: 'Mes travaux',
    credit: 'Solde',
    notifications: 'Notifications',
    account: 'Compte',
    disputes: 'Litiges',
    reports: 'Signalements',
    dashboard: 'Tableau de bord',
    approvals: 'Validations',
    users: 'Utilisateurs',
    finance: 'Finances',
    catalog: 'Métiers et villes',
    settings: 'Paramètres',
    audit: 'Journal',
  },
  notBuilt: {
    title: 'Écran pas encore construit',
    body: 'L’écran {{screen}} est spécifié dans docs/SCREENS.md et arrive à la prochaine phase.',
  },
  notFound: {
    title: 'Page introuvable',
    cta: 'Retour à l’accueil',
  },
  forbidden: {
    title: 'Cette page n’est pas pour vous',
    body: 'Votre compte ({{role}}) n’a pas accès ici.',
    cta: 'Retour à votre espace',
  },
} as const

const en = {
  common: {
    appName: 'Brikole',
    loading: 'Loading…',
    retry: 'Try again',
    cancel: 'Cancel',
    confirm: 'Confirm',
    save: 'Save',
    back: 'Back',
    next: 'Next',
    search: 'Search',
    close: 'Close',
    optional: 'optional',
    signIn: 'Sign in',
    signOut: 'Sign out',
    signUp: 'Create account',
    language: 'Language',
    theme: 'Appearance',
    themeLight: 'Light',
    themeDark: 'Dark',
    themeSystem: 'System',
  },
  provider: {
    topRated: 'Top rated',
    newHere: 'New here',
    jobsDone: '{{count}} jobs',
    startingAt: 'starting at',
    onQuote: 'On quote',
  },
  roles: {
    client: 'Client',
    provider: 'M3allem',
    moderator: 'Moderator',
    admin: 'Admin',
  },
  landing: {
    title: 'Find the right m3allem, fast',
    subtitle: 'Plumber, electrician, painter, carpenter… Describe the job, get priced offers.',
    ctaClient: 'Request a service',
    ctaProvider: 'Become a m3allem',
    searchPlaceholder: 'Which service?',
    searchCta: 'Search',
    popular: 'Most asked for',
    city: 'City',
    cityAll: 'All cities',
    providersOne: '1 m3allem',
    providersMany: '{{count}} m3allems',
    noProviderHere: 'Nobody yet',
    countsInCity: 'in {{city}}',
    countsEverywhere: 'across Morocco',
    trustNote: 'No commission on the price · Paid in cash, straight to the tradesman',
    topProviders: 'Top rated m3allems',
    seeAll: 'See all',
    noProviders: 'No tradesman in this city yet',
    browseByTrade: 'Browse by trade',
    tradesTitle: 'Trades',
    tradesEmpty: 'No trade yet',
    howTitle: 'How it works',
    how1Title: 'Describe the job',
    how1Body: 'What needs doing, where, and when. Add photos if you like.',
    how2Title: 'Get offers',
    how2Body: 'Tradesmen in your trade and your city send you their price.',
    how3Title: 'Pick one, pay cash',
    how3Body: 'You choose, then pay the tradesman directly. The platform never touches the money.',
    forProsTitle: 'Are you a m3allem?',
    forProsBody: 'Get job requests from clients in your city. No commission on the job price, no subscription — you only pay when your offer is accepted.',
  },
  auth: {
    phone: 'Phone number',
    phoneHint: 'The number people reach you on',
    fullName: 'Full name',
    password: 'Password',
    passwordHint: 'At least 8 characters, with a letter and a digit',
    currentPassword: 'Current password',
    newPassword: 'New password',
    loginTitle: 'Welcome back',
    loginSubtitle: 'Sign in to carry on.',
    registerSubtitle: 'One minute, and you are set.',
    show: 'Show',
    hide: 'Hide',
    promise1: 'Priced offers, usually within a few hours.',
    promise2: 'Real ratings, from real clients.',
    promise3: 'You pay the tradesman in cash, once the work is done.',
    loginCta: 'Sign in',
    noAccount: 'No account yet?',
    haveAccount: 'Already have an account?',
    registerTitle: 'Create an account',
    registerCta: 'Create account',
    chooseRole: 'You are here to…',
    roleClientTitle: 'I need a job done',
    roleClientBody: 'You describe the work, you get offers.',
    roleProviderTitle: 'I am a m3allem',
    roleProviderBody: 'You get requests and send your offers.',
    roleLockedNote: 'The account type cannot be changed later, except by an admin.',
    forgot: 'Forgot your password?',
    forgotBody: 'For now an admin has to reset it. SMS reset comes later.',
  },
  errors: {
    generic: 'Something went wrong. Try again.',
    network: 'Could not reach the server. Check your connection.',
    phone_invalid: 'That number is not valid. Example: 0612345678',
    password_too_weak: 'The password needs at least 8 characters, with a letter and a digit.',
    validation_failed: 'Something is missing or incorrect.',
    phone_taken: 'That number already has an account.',
    invalid_credentials: 'Wrong number or password.',
    account_locked: 'Account temporarily locked. Try again in {{minutes}} minutes.',
    account_suspended: 'This account is suspended.',
    role_not_self_registerable: 'That account type is created by an admin.',
    not_authenticated: 'You need to sign in.',
    forbidden: 'You do not have access to this page.',
    token_expired: 'Session expired. Sign in again.',
    token_invalid: 'Invalid session. Sign in again.',
    token_wrong_type: 'Invalid session. Sign in again.',
    not_found: 'Not found.',
    conflict: 'That has already been done.',
    insufficient_credit: 'Not enough credit.',
    amount_invalid: 'That amount is not valid.',
  },
  nav: {
    newRequest: 'New request',
    myRequests: 'My requests',
    requests: 'Requests',
    myOffers: 'My offers',
    myJobs: 'My jobs',
    credit: 'Credit',
    notifications: 'Notifications',
    account: 'Account',
    disputes: 'Disputes',
    reports: 'Reports',
    dashboard: 'Dashboard',
    approvals: 'Approvals',
    users: 'Users',
    finance: 'Finance',
    catalog: 'Trades and cities',
    settings: 'Settings',
    audit: 'Audit log',
  },
  notBuilt: {
    title: 'This screen is not built yet',
    body: 'Screen {{screen}} is specified in docs/SCREENS.md and lands in the next phase.',
  },
  notFound: {
    title: 'Page not found',
    cta: 'Back to home',
  },
  forbidden: {
    title: 'This page is not yours',
    body: 'Your account ({{role}}) has no access here.',
    cta: 'Back to your area',
  },
} as const

export const resources = {
  ar: { translation: ar },
  fr: { translation: fr },
  en: { translation: en },
} as const

export function isRtl(language: Language): boolean {
  return RTL_LANGUAGES.includes(language)
}

export function readStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && (LANGUAGES as readonly string[]).includes(stored)) return stored as Language
  } catch {
    // Site data blocked. Arabic is the default and a fine answer.
  }
  return DEFAULT_LANGUAGE
}

/**
 * Point the document at a language.
 *
 * `dir` on <html> is what makes the whole layout mirror, which is why every
 * component uses logical properties (`ms-*`, `text-start`) rather than left
 * and right — they follow this automatically.
 */
export function applyLanguage(language: Language): void {
  const root = document.documentElement
  root.lang = language
  root.dir = isRtl(language) ? 'rtl' : 'ltr'
}

export async function setLanguage(language: Language): Promise<void> {
  await i18next.changeLanguage(language)
  try {
    localStorage.setItem(STORAGE_KEY, language)
  } catch {
    // Not remembering it is not a reason to fail to apply it.
  }
  applyLanguage(language)
}

export function initI18n(language: Language = readStoredLanguage()) {
  void i18next.use(initReactI18next).init({
    resources,
    lng: language,
    fallbackLng: DEFAULT_LANGUAGE,
    interpolation: { escapeValue: false },
    returnNull: false,
  })
  applyLanguage(language)
  return i18next
}

export default i18next
