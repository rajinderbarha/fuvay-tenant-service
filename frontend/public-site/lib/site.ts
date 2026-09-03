export const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://fuvay.com";
export const links = {
  whatsapp: process.env.NEXT_PUBLIC_WHATSAPP_BOOKING_URL || "/contact/",
  instagram: process.env.NEXT_PUBLIC_INSTAGRAM_BOOKING_URL || "https://instagram.com/fuvaymultitenant",
  app: process.env.NEXT_PUBLIC_CUSTOMER_APP_URL || "/contact/",
  provider: process.env.NEXT_PUBLIC_PROVIDER_PORTAL_URL || "/providers/",
};

export const services = [
  { slug: "ac-service-repair", name: "AC Service & Repair", punjabi: "ਏਸੀ ਸਰਵਿਸ ਅਤੇ ਮੁਰੰਮਤ", image: "/services/ac-hvac-3d.png", description: "AC inspection, service, gas-refill diagnosis and repair from providers serving your PIN code." },
  { slug: "washing-machine-repair", name: "Washing Machine Repair", punjabi: "ਵਾਸ਼ਿੰਗ ਮਸ਼ੀਨ ਮੁਰੰਮਤ", image: "/services/washing-machine-3d.png", description: "Book diagnosis and repair for common washing machine faults at home." },
  { slug: "refrigerator-repair", name: "Refrigerator Repair", punjabi: "ਫ੍ਰਿਜ ਮੁਰੰਮਤ", image: "/services/refrigerator-3d.png", description: "Home visits for cooling, leakage, compressor and electrical refrigerator issues." },
  { slug: "ro-water-purifier-service", name: "RO Water Purifier Service", punjabi: "ਆਰਓ ਵਾਟਰ ਪਿਊਰੀਫਾਇਰ ਸਰਵਿਸ", image: "/services/ro-water-purifier-3d.png", description: "RO service, filter checks and fault diagnosis by local service providers." },
  { slug: "geyser-repair", name: "Geyser Repair", punjabi: "ਗੀਜ਼ਰ ਮੁਰੰਮਤ", image: "/services/geyser-3d.png", description: "Inspection and repair for heating, leakage and electrical geyser problems." },
  { slug: "chimney-service", name: "Kitchen Chimney Service", punjabi: "ਕਿਚਨ ਚਿਮਨੀ ਸਰਵਿਸ", image: "/services/chimney-3d.png", description: "Kitchen chimney cleaning, inspection and repair at your address." },
] as const;

export const cities = ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Mohali", "Bathinda", "Hoshiarpur", "Pathankot"].map(name => ({ name, slug: name.toLowerCase() }));
