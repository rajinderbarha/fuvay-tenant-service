/**
 * ServiceOS — Bot Translations
 * Languages: Punjabi (pa) → Hindi (hi) → English (en)
 * Regional language shown first as per product requirement.
 */

export type Lang = "pa" | "hi" | "en";

export const LANG_LABELS: Record<Lang, string> = {
  pa: "ਪੰਜਾਬੀ",
  hi: "हिंदी",
  en: "English",
};

// Cycling loading phrases shown during shimmer animation
export const LOADING_PHRASES: Record<Lang, string[]> = {
  pa: [
    "ਜਾਣਕਾਰੀ ਇਕੱਠੀ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ...",
    "ਸੇਵਾ ਦੀ ਕੀਮਤ ਦੇਖ ਰਹੇ ਹਾਂ...",
    "ਸਹੀ ਵਿਕਲਪ ਲੱਭ ਰਹੇ ਹਾਂ...",
    "ਤੁਹਾਡੇ ਲਈ ਤਿਆਰ ਕਰ ਰਹੇ ਹਾਂ...",
    "ਤਕਨੀਸ਼ੀਅਨ ਦੀ ਜਾਣਕਾਰੀ ਲੈ ਰਹੇ ਹਾਂ...",
    "ਕੀਮਤਾਂ ਦੀ ਜਾਂਚ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ...",
  ],
  hi: [
    "जानकारी एकत्र की जा रही है...",
    "सेवा की कीमत देख रहे हैं...",
    "सही विकल्प खोज रहे हैं...",
    "आपके लिए तैयार कर रहे हैं...",
    "तकनीशियन की जानकारी ले रहे हैं...",
    "कीमतें जाँच रहे हैं...",
  ],
  en: [
    "Checking your issue...",
    "Finding available services...",
    "Looking up prices...",
    "Getting ready for you...",
    "Finding technicians near you...",
    "Checking service availability...",
  ],
};

// Bot greeting when category is opened
export const BOT_GREETING: Record<Lang, Record<string, string>> = {
  pa: {
    ac:             "ਤੁਹਾਡੇ AC ਨਾਲ ਕੀ ਸਮੱਸਿਆ ਹੈ?",
    plumbing:       "ਪਲੰਬਿੰਗ ਨਾਲ ਕੀ ਸਮੱਸਿਆ ਆਈ ਹੈ?",
    electrical:     "ਬਿਜਲੀ ਨਾਲ ਸੰਬੰਧਿਤ ਕੀ ਸਮੱਸਿਆ ਹੈ?",
    cleaning:       "ਕੀ ਸਾਫ਼ ਕਰਵਾਉਣਾ ਹੈ?",
    pest_control:   "ਕਿਹੜੇ ਕੀੜੇ-ਮਕੌੜਿਆਂ ਦੀ ਸਮੱਸਿਆ ਹੈ?",
    appliances:     "ਕਿਹੜੇ ਉਪਕਰਣ ਵਿੱਚ ਖ਼ਰਾਬੀ ਹੈ?",
    painting:       "ਕਿਸ ਤਰ੍ਹਾਂ ਦਾ ਰੰਗ-ਰੋਗਣ ਦਾ ਕੰਮ ਚਾਹੀਦਾ ਹੈ?",
    carpentry:      "ਤਰਖਾਣ ਦੇ ਕੰਮ ਵਿੱਚ ਕੀ ਚਾਹੀਦਾ ਹੈ?",
    waterproofing:  "ਪਾਣੀ ਕਿੱਥੋਂ ਆ ਰਿਹਾ ਹੈ?",
    interior_design:"ਡਿਜ਼ਾਈਨ ਲਈ ਕੀ ਸਲਾਹ ਚਾਹੀਦੀ ਹੈ?",
  },
  hi: {
    ac:             "आपके AC में क्या समस्या है?",
    plumbing:       "प्लंबिंग में क्या परेशानी आई है?",
    electrical:     "बिजली से संबंधित क्या समस्या है?",
    cleaning:       "क्या साफ़ करवाना है?",
    pest_control:   "किस कीड़े-मकोड़े की समस्या है?",
    appliances:     "किस उपकरण में खराबी है?",
    painting:       "किस तरह का पेंट का काम चाहिए?",
    carpentry:      "बढ़ईगिरी के काम में क्या चाहिए?",
    waterproofing:  "पानी कहाँ से आ रहा है?",
    interior_design:"डिज़ाइन के लिए क्या सलाह चाहिए?",
  },
  en: {
    ac:             "What's happening with your AC?",
    plumbing:       "What's the plumbing issue?",
    electrical:     "What's the electrical problem?",
    cleaning:       "What needs to be cleaned?",
    pest_control:   "What kind of pest problem?",
    appliances:     "Which appliance needs help?",
    painting:       "What painting work do you need?",
    carpentry:      "What carpentry work do you need?",
    waterproofing:  "What's the water issue?",
    interior_design:"What kind of design help do you need?",
  },
};

// Option labels per category per language (same order as TREE opts)
export const OPT_LABELS: Record<Lang, Record<string, string[]>> = {
  pa: {
    ac:             ["ਠੰਡਾ ਨਹੀਂ ਕਰ ਰਿਹਾ","ਚਾਲੂ ਨਹੀਂ ਹੋ ਰਿਹਾ","ਪਾਣੀ ਲੀਕ ਹੋ ਰਿਹਾ ਹੈ","ਅਜੀਬ ਆਵਾਜ਼ ਆ ਰਹੀ ਹੈ","ਸਾਲਾਨਾ ਸਰਵਿਸ ਚਾਹੀਦੀ","ਡੂੰਘੀ ਸਫ਼ਾਈ ਚਾਹੀਦੀ","ਗੈਸ ਰੀਫਿਲ ਚਾਹੀਦੀ","ਮਾਹਰ ਦੀ ਜਾਂਚ ਚਾਹੀਦੀ"],
    ac_how_long:    ["ਅੱਜ ਹੀ ਸ਼ੁਰੂ ਹੋਈ","ਕੁਝ ਦਿਨਾਂ ਤੋਂ","ਕਈ ਹਫ਼ਤਿਆਂ ਤੋਂ"],
    plumbing:       ["ਪਾਈਪ ਲੀਕ ਹੋ ਰਹੀ ਹੈ","ਟੂਟੀ ਵਿੱਚ ਸਮੱਸਿਆ ਹੈ","ਨਾਲੀ ਜਾਮ ਹੈ","ਟਾਇਲਟ ਖ਼ਰਾਬ ਹੈ","ਟੈਂਕ ਦੀ ਸਫ਼ਾਈ ਚਾਹੀਦੀ","ਡਰੇਨ ਸਰਵਿਸ ਚਾਹੀਦੀ","ਮਾਹਰ ਦੀ ਜਾਂਚ ਚਾਹੀਦੀ"],
    electrical:     ["ਬਿਜਲੀ ਨਹੀਂ ਆ ਰਹੀ","ਸਾਕਟ ਜਾਂ ਸਵਿੱਚ ਖ਼ਰਾਬ","ਪੱਖਾ ਜਾਂ ਬੱਲਬ ਨਹੀਂ ਚੱਲਦਾ","ਸੁਰੱਖਿਆ ਜਾਂਚ ਚਾਹੀਦੀ","ਨਵੀਂ ਵਾਇਰਿੰਗ ਦੀ ਯੋਜਨਾ"],
    cleaning:       ["ਪੂਰੇ ਘਰ ਦੀ ਸਫ਼ਾਈ","ਰਸੋਈ ਦੀ ਸਫ਼ਾਈ","ਬਾਥਰੂਮ ਦੀ ਸਫ਼ਾਈ","ਸੋਫ਼ਾ ਜਾਂ ਕਾਰਪੇਟ ਦੀ ਸਫ਼ਾਈ"],
    pest_control:   ["ਕਾਕਰੋਚ ਜਾਂ ਕੀੜੀਆਂ","ਚੂਹੇ","ਦੀਮਕ","ਖਟਮਲ","ਮਾਹਰ ਦੀ ਜਾਂਚ ਚਾਹੀਦੀ"],
    appliances:     ["ਵਾਸ਼ਿੰਗ ਮਸ਼ੀਨ","ਫ਼੍ਰਿੱਜ","ਮਾਈਕ੍ਰੋਵੇਵ","ਗੀਜ਼ਰ","RO / ਪਾਣੀ ਫ਼ਿਲਟਰ"],
    appliance_wm:   ["ਧੋਂਦੀ ਨਹੀਂ","ਪਾਣੀ ਲੀਕ","ਸਾਲਾਨਾ ਸਰਵਿਸ"],
    appliance_geyser:["ਗਰਮ ਨਹੀਂ ਕਰਦਾ","ਲੀਕ ਹੋ ਰਿਹਾ ਹੈ","ਸਾਲਾਨਾ ਸਰਵਿਸ"],
    painting:       ["ਇੱਕ ਕਮਰਾ","ਪੂਰਾ ਘਰ","ਵਾਲਪੇਪਰ","ਰੰਗ ਸਲਾਹ","ਦੀਵਾਰ ਦੀ ਜਾਂਚ"],
    carpentry:      ["ਫ਼ਰਨੀਚਰ ਟੁੱਟਿਆ ਹੈ","ਦਰਵਾਜ਼ਾ ਜਾਂ ਖਿੜਕੀ ਖ਼ਰਾਬ","ਫ਼ਰਨੀਚਰ ਜੋੜਨਾ ਹੈ","ਕਿਚਨ / ਵਾਰਡਰੋਬ ਯੋਜਨਾ"],
    waterproofing:  ["ਛੱਤ ਤੋਂ ਪਾਣੀ ਆ ਰਿਹਾ ਹੈ","ਬਾਥਰੂਮ ਵਿੱਚੋਂ ਸਿੱਲ ਆਉਂਦੀ ਹੈ","ਦੀਵਾਰਾਂ 'ਤੇ ਨਮੀ","ਰੋਕਥਾਮ ਲਈ ਪਾਣੀ-ਰੋਕੂ ਕੋਟਿੰਗ"],
    interior_design:["ਪੂਰੇ ਘਰ ਦਾ ਡਿਜ਼ਾਈਨ","ਮੋਡਿਊਲਰ ਕਿਚਨ ਯੋਜਨਾ","ਅਲਮਾਰੀ / ਸਟੋਰੇਜ਼ ਡਿਜ਼ਾਈਨ"],
  },
  hi: {
    ac:             ["ठंडा नहीं कर रहा","चालू नहीं हो रहा","पानी टपक रहा है","अजीब आवाज़ आ रही है","सालाना सर्विस चाहिए","डीप क्लीनिंग चाहिए","गैस रिफिल चाहिए","एक्सपर्ट इंस्पेक्शन चाहिए"],
    ac_how_long:    ["आज ही शुरू हुआ","कुछ दिनों से","कई हफ्तों से"],
    plumbing:       ["पाइप लीक हो रही है","नल में समस्या है","नाली जाम है","टॉयलेट खराब है","टंकी की सफाई चाहिए","ड्रेन सर्विस चाहिए","एक्सपर्ट जाँच चाहिए"],
    electrical:     ["बिजली नहीं आ रही","सॉकेट या स्विच खराब है","पंखा या बल्ब नहीं चलता","सुरक्षा जाँच चाहिए","नई वायरिंग की योजना"],
    cleaning:       ["पूरे घर की सफाई","रसोई की सफाई","बाथरूम की सफाई","सोफा या कार्पेट की सफाई"],
    pest_control:   ["तिलचट्टे या चींटियाँ","चूहे","दीमक","खटमल","एक्सपर्ट जाँच चाहिए"],
    appliances:     ["वाशिंग मशीन","फ्रिज","माइक्रोवेव","गीज़र","RO / वाटर फिल्टर"],
    appliance_wm:   ["धो नहीं रही","पानी लीक हो रहा","सालाना सर्विस चाहिए"],
    appliance_geyser:["गर्म नहीं कर रहा","लीक हो रहा है","सालाना सर्विस चाहिए"],
    painting:       ["एक कमरा","पूरा घर","वॉलपेपर","रंग सलाह","दीवार की जाँच"],
    carpentry:      ["फर्नीचर टूटा है","दरवाज़ा या खिड़की खराब","फर्नीचर जोड़ना है","किचन / वॉर्डरोब योजना"],
    waterproofing:  ["छत से पानी आ रहा है","बाथरूम में सीलन है","दीवारों पर नमी","रोकथाम के लिए कोटिंग"],
    interior_design:["पूरे घर का डिज़ाइन","मॉड्यूलर किचन योजना","अलमारी / स्टोरेज डिज़ाइन"],
  },
  en: {
    ac:             ["Not cooling properly","Not switching on","Water leaking from unit","Making strange noises","Annual service","Deep chemical cleaning","Gas refill needed","Not sure — need expert"],
    ac_how_long:    ["Just started today","Past few days","Weeks or longer"],
    plumbing:       ["Pipe is leaking","Tap or faucet problem","Drain is blocked","Toilet not working","Tank cleaning needed","Drain cleaning service","Want a plumbing check"],
    electrical:     ["No power / circuit tripped","Socket or switch not working","Fan or light not working","Safety audit for home","Planning new wiring"],
    cleaning:       ["Full home deep clean","Kitchen only","Bathrooms","Sofa or carpets"],
    pest_control:   ["Cockroaches or ants","Rats or mice","Termites","Bed bugs","Not sure — need inspection"],
    appliances:     ["Washing machine","Refrigerator / Fridge","Microwave","Water heater / Geyser","RO / Water purifier"],
    appliance_wm:   ["Not spinning / draining","Leaking water","Annual service / checkup"],
    appliance_geyser:["Not heating water","Leaking","Annual service"],
    painting:       ["One room","Full home / flat","Wallpaper","Colour consultation","Wall crack / seepage advice"],
    carpentry:      ["Furniture broken","Door or window problem","Assemble new furniture","Modular kitchen / wardrobe plan"],
    waterproofing:  ["Roof / terrace leaking","Bathroom seepage","Damp / wet walls","Preventive waterproofing"],
    interior_design:["Full home interior design","Modular kitchen planning","Wardrobe / storage design"],
  },
};

// Booking confirmation messages
export const BOOKING_MSG: Record<Lang, (service: string, price: string) => string> = {
  pa: (s, p) => `ਵਧੀਆ! ਮੈਂ **${s}** ਦੀ ਸਿਫ਼ਾਰਸ਼ ਕਰਦਾ ਹਾਂ।\n\n${p}\n\nਤਕਨੀਸ਼ੀਅਨ ਕਦੋਂ ਆਵੇ?`,
  hi: (s, p) => `बढ़िया! मैं **${s}** की सिफारिश करता हूँ।\n\n${p}\n\nतकनीशियन कब आए?`,
  en: (s, p) => `Perfect! I recommend **${s}**.\n\n${p}\n\nWhen should the technician come?`,
};

export const SOMETHING_ELSE: Record<Lang, string> = {
  pa: "✏️ ਕੁਝ ਹੋਰ ਦੱਸੋ",
  hi: "✏️ कुछ और बताएं",
  en: "✏️ Something else",
};

export const INPUT_PLACEHOLDER: Record<Lang, string> = {
  pa: "ਆਪਣੀ ਸਮੱਸਿਆ ਦੱਸੋ...",
  hi: "अपनी समस्या बताएं...",
  en: "Or type your issue here…",
};
