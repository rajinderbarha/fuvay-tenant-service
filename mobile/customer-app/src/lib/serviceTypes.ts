/**
 * ServiceOS — Category-Driven Service Catalog
 *
 * DESIGN PRINCIPLE: Available job types vary by service category.
 *   • AC & HVAC:       Repair ✓  Maintenance ✓  Consultation ✓
 *   • Home Cleaning:   Repair ✗  Maintenance ✓  Consultation ✗
 *   • Pest Control:    Repair ✗  Maintenance ✓  Consultation ✓
 *   • Painting:        Repair ✗  Maintenance ✓  Consultation ✓
 *   • Carpentry:       Repair ✓  Maintenance ✓  Consultation ✓
 *   • Interior Design: Repair ✗  Maintenance ✗  Consultation ✓
 *   • Locksmith:       Repair ✓  Maintenance ✓  Consultation ✗
 *   etc.
 *
 * Flow:
 *  1. Customer picks a CATEGORY (AC, Plumbing, Cleaning…)
 *  2. If category has >1 available types → show only those type options
 *     If category has exactly 1 type → skip type selector entirely
 *  3. Customer picks specific SERVICE from that category+type
 *  4. Schedule + Confirm
 */

export type ServiceJobType = "repair" | "maintenance" | "consultation";

export interface ServiceItem {
  name:        string;
  icon:        string;
  jobType:     ServiceJobType;
  visitFee?:   number;   // repair: assessment fee charged upfront — NO estimate shown
  fixedPrice?: number;   // maintenance: full price shown at booking
  consultFee?: number;   // consultation: fixed fee always charged
  description: string;
  duration:    string;
  checklist?:  string[]; // maintenance: what gets done (shown to customer)
}

export interface ServiceCategory {
  id:             string;
  name:           string;
  icon:           string;
  description:    string;
  availableTypes: ServiceJobType[];  // ONLY these types apply to this category
  services:       ServiceItem[];
}

// ── Type metadata ─────────────────────────────────────────────────────────────
export const JOB_TYPE_META: Record<ServiceJobType, {
  label:string; icon:string; tagline:string;
  color:string; bg:string; border:string;
}> = {
  repair: {
    label:   "Fix a Problem",
    icon:    "🔧",
    tagline: "Something is broken — technician inspects, quotes, then fixes.",
    color:   "#DC2626", bg:"#FEF2F2", border:"#FECACA",
  },
  maintenance: {
    label:   "Book a Service",
    icon:    "⚙️",
    tagline: "Scheduled work at a fixed price — no surprises.",
    color:   "#16A34A", bg:"#F0FDF4", border:"#BBF7D0",
  },
  consultation: {
    label:   "Get Expert Advice",
    icon:    "📋",
    tagline: "Expert assesses and gives you a report — may include a repair quote.",
    color:   "#7C3AED", bg:"#F5F3FF", border:"#DDD6FE",
  },
};

// ── Full service catalog ───────────────────────────────────────────────────────
export const SERVICE_CATEGORIES: ServiceCategory[] = [

  // ── AC & Air Conditioning ── ALL 3 TYPES ──────────────────────────────────
  {
    id:"ac", name:"AC & Air Conditioning", icon:"❄️",
    description:"Repair, service and expert advice for all AC brands",
    availableTypes:["repair","maintenance","consultation"],
    services:[
      // Repair
      { name:"AC Not Cooling",    icon:"❄️", jobType:"repair",      visitFee:199,
        description:"AC running but not cooling properly or cooling unevenly",       duration:"45-90 min" },
      { name:"AC Not Switching On",icon:"🔌", jobType:"repair",     visitFee:199,
        description:"AC completely dead, won't power on, trips the breaker",         duration:"45-90 min" },
      { name:"AC Water Leaking",  icon:"💧", jobType:"repair",      visitFee:199,
        description:"Water dripping from indoor unit or collecting on floor",         duration:"30-60 min" },
      { name:"AC Making Noise",   icon:"🔊", jobType:"repair",      visitFee:199,
        description:"Rattling, buzzing, grinding or unusual sounds from AC",         duration:"30-60 min" },
      // Maintenance
      { name:"AC Annual Service", icon:"🧹", jobType:"maintenance", fixedPrice:699,
        description:"Filter clean, coil clean, drain flush, performance test",        duration:"90 min",
        checklist:["Clean/replace air filter","Clean evaporator coils","Flush drain pipe","Check refrigerant pressure","Inspect wiring","Performance test"] },
      { name:"AC Deep Cleaning",  icon:"🫧", jobType:"maintenance", fixedPrice:1299,
        description:"Chemical deep clean of indoor + outdoor unit",                  duration:"2 hrs",
        checklist:["Chemical wash of indoor unit","Chemical clean of outdoor coil","Deep clean of drain tray","Foam jet cleaning","Performance test"] },
      { name:"AC Gas Refill",     icon:"💨", jobType:"maintenance", fixedPrice:2499,
        description:"Refrigerant pressure check and gas top-up (R22/R32/R410A)",    duration:"60 min" },
      // Consultation
      { name:"AC Inspection Report",icon:"📋", jobType:"consultation", consultFee:299,
        description:"Full AC health check with detailed condition report and repair estimate", duration:"45 min" },
      { name:"New AC Buying Advice",icon:"🏷️", jobType:"consultation", consultFee:199,
        description:"Expert recommends the right AC size and brand for your room",   duration:"30 min" },
    ],
  },

  // ── Plumbing ── ALL 3 TYPES ────────────────────────────────────────────────
  {
    id:"plumbing", name:"Plumbing", icon:"🔧",
    description:"All plumbing repairs, installations and assessments",
    availableTypes:["repair","maintenance","consultation"],
    services:[
      { name:"Pipe Leaking",         icon:"💧", jobType:"repair",      visitFee:149,
        description:"Water pipe, joint or fitting leaking",                          duration:"30-60 min" },
      { name:"Tap / Faucet Problem", icon:"🚿", jobType:"repair",      visitFee:149,
        description:"Tap not closing, low pressure, broken handle, dripping",        duration:"20-45 min" },
      { name:"Drain Blocked",        icon:"🚽", jobType:"repair",      visitFee:149,
        description:"Sink, toilet, bathroom or kitchen drain blocked",               duration:"30-90 min" },
      { name:"Toilet Repair",        icon:"🚾", jobType:"repair",      visitFee:149,
        description:"Toilet not flushing, constantly running, leaking base",         duration:"30-60 min" },
      { name:"Drain Cleaning Service",icon:"🧹", jobType:"maintenance", fixedPrice:599,
        description:"High-pressure jet cleaning of all drains — preventive care",   duration:"60 min" },
      { name:"Water Tank Cleaning",  icon:"💧", jobType:"maintenance", fixedPrice:799,
        description:"Overhead or underground tank cleaning and disinfection",        duration:"2-3 hrs" },
      { name:"Plumbing Assessment",  icon:"📋", jobType:"consultation", consultFee:299,
        description:"Full home plumbing check — identify risks, get a repair plan", duration:"45 min" },
      { name:"Bathroom Renovation Consultation",icon:"🛁", jobType:"consultation", consultFee:499,
        description:"Expert plan for your bathroom renovation with cost estimate",   duration:"60 min" },
    ],
  },

  // ── Electrical ── ALL 3 TYPES ─────────────────────────────────────────────
  {
    id:"electrical", name:"Electrical", icon:"⚡",
    description:"All electrical repairs, safety checks and installations",
    availableTypes:["repair","maintenance","consultation"],
    services:[
      { name:"No Power / Short Circuit", icon:"⚡", jobType:"repair",   visitFee:199,
        description:"Power outage in a room, circuit tripping, short circuit",       duration:"30-90 min" },
      { name:"Socket / Switch Repair",   icon:"🔌", jobType:"repair",   visitFee:149,
        description:"Socket not working, loose switch, sparking outlet",             duration:"20-45 min" },
      { name:"Fan / Light Not Working",  icon:"💡", jobType:"repair",   visitFee:149,
        description:"Ceiling fan, light fixture or tube light not working",          duration:"20-45 min" },
      { name:"Electrical Safety Audit",  icon:"🛡️", jobType:"maintenance", fixedPrice:499,
        description:"Full home wiring inspection, earthing test, overload check",   duration:"60 min",
        checklist:["Inspect all wiring","Test earthing","Check MCB/fuse box","Test all sockets","Check for overloads","Written safety report"] },
      { name:"Electrical Home Audit",    icon:"📋", jobType:"consultation", consultFee:399,
        description:"Expert audit of home wiring with upgrade recommendations",      duration:"60 min" },
      { name:"New Wiring Consultation",  icon:"🏗️", jobType:"consultation", consultFee:499,
        description:"Plan and cost estimate for new home wiring or rewiring",        duration:"60 min" },
    ],
  },

  // ── Home Cleaning ── MAINTENANCE ONLY ─────────────────────────────────────
  {
    id:"cleaning", name:"Home Cleaning", icon:"🧹",
    description:"Professional cleaning for your entire home",
    availableTypes:["maintenance"],  // ONLY maintenance — no repair, no consultation
    services:[
      { name:"Home Deep Cleaning",    icon:"🏠", jobType:"maintenance", fixedPrice:1999,
        description:"Full home deep clean — rooms, kitchen, bathrooms, floors",      duration:"4-6 hrs",
        checklist:["Vacuum and mop all rooms","Deep clean bathrooms","Degrease kitchen","Clean fans and lights","Wipe doors and windows"] },
      { name:"Kitchen Deep Clean",    icon:"🍳", jobType:"maintenance", fixedPrice:1299,
        description:"Deep clean kitchen including chimney, slab, cabinets, sink",   duration:"3 hrs" },
      { name:"Bathroom Deep Clean",   icon:"🚿", jobType:"maintenance", fixedPrice:799,
        description:"Scrub tiles, clean fixtures, descale, sanitise",               duration:"2 hrs" },
      { name:"Sofa / Carpet Cleaning",icon:"🛋️", jobType:"maintenance", fixedPrice:999,
        description:"Foam cleaning of sofas and dry cleaning of carpets",           duration:"2-3 hrs" },
      { name:"Office Deep Cleaning",  icon:"🏢", jobType:"maintenance", fixedPrice:2999,
        description:"Professional deep cleaning for office spaces",                  duration:"4-8 hrs" },
    ],
  },

  // ── Pest Control ── MAINTENANCE + CONSULTATION (no repair) ────────────────
  {
    id:"pest_control", name:"Pest Control", icon:"🪲",
    description:"Professional pest treatment and prevention",
    availableTypes:["maintenance","consultation"],  // no "repair"
    services:[
      { name:"General Pest Control",  icon:"🦟", jobType:"maintenance", fixedPrice:999,
        description:"Treatment for cockroaches, ants, spiders, silverfish",          duration:"2-3 hrs",
        checklist:["Spray kitchen and bathrooms","Treat cracks and entry points","Gel bait placement","Post-treatment report"] },
      { name:"Rodent Control",        icon:"🐭", jobType:"maintenance", fixedPrice:1499,
        description:"Rat and mouse removal with traps and repellent",               duration:"2-3 hrs" },
      { name:"Termite Treatment",     icon:"🪳", jobType:"maintenance", fixedPrice:3999,
        description:"Anti-termite treatment — drill, inject, seal",                 duration:"4-6 hrs" },
      { name:"Bed Bug Treatment",     icon:"🛏️", jobType:"maintenance", fixedPrice:2499,
        description:"Heat + chemical treatment for bed bugs",                       duration:"3-4 hrs" },
      { name:"Pest Inspection Report",icon:"📋", jobType:"consultation", consultFee:299,
        description:"Expert identifies all pest issues and recommends the right treatment", duration:"45 min" },
    ],
  },

  // ── Painting & Walls ── MAINTENANCE + CONSULTATION (no repair) ────────────
  {
    id:"painting", name:"Painting & Walls", icon:"🎨",
    description:"Professional painting and wall work for home and office",
    availableTypes:["maintenance","consultation"],  // no "repair"
    services:[
      { name:"Single Room Painting",  icon:"🖌️", jobType:"maintenance", fixedPrice:4999,
        description:"Interior wall painting — one room. Labour only, paint extra.",  duration:"1-2 days" },
      { name:"Full Home Painting",    icon:"🏠", jobType:"maintenance", fixedPrice:24999,
        description:"2BHK full interior painting — labour + primer. Paint extra.",  duration:"3-5 days" },
      { name:"Exterior Painting",     icon:"🏗️", jobType:"maintenance", fixedPrice:14999,
        description:"Exterior wall waterproofing and painting",                      duration:"2-4 days" },
      { name:"Wallpaper Installation",icon:"🖼️", jobType:"maintenance", fixedPrice:2999,
        description:"Professional wallpaper installation — one wall. Wallpaper extra.", duration:"1 day" },
      { name:"Painting Consultation", icon:"🎨", jobType:"consultation", consultFee:499,
        description:"Colour expert advises on palette, materials and cost estimate", duration:"45 min" },
      { name:"Wall Crack / Seepage Consultation",icon:"🔍", jobType:"consultation", consultFee:399,
        description:"Expert assesses wall cracks or seepage and recommends solution", duration:"45 min" },
    ],
  },

  // ── Carpentry ── ALL 3 TYPES ───────────────────────────────────────────────
  {
    id:"carpentry", name:"Carpentry & Furniture", icon:"🪵",
    description:"Furniture repair, assembly and custom woodwork",
    availableTypes:["repair","maintenance","consultation"],
    services:[
      { name:"Furniture Repair",       icon:"🔨", jobType:"repair",      visitFee:149,
        description:"Broken chair, loose table, cracked cabinet, damaged furniture", duration:"30-90 min" },
      { name:"Door / Window Problem",  icon:"🚪", jobType:"repair",      visitFee:149,
        description:"Door not closing, hinge loose, drawer stuck, handle broken",   duration:"30-60 min" },
      { name:"Furniture Assembly",     icon:"🔩", jobType:"maintenance", fixedPrice:499,
        description:"Assemble flat-pack or new furniture (per item)",               duration:"60-120 min" },
      { name:"Renovation Consultation",icon:"📐", jobType:"consultation", consultFee:599,
        description:"Expert plan for modular kitchen, wardrobe or home renovation", duration:"60 min" },
    ],
  },

  // ── Appliance Repair ── REPAIR + MAINTENANCE (no consultation) ────────────
  {
    id:"appliances", name:"Appliance Repair", icon:"🏠",
    description:"Repair and servicing of all home appliances",
    availableTypes:["repair","maintenance"],  // no consultation
    services:[
      { name:"Washing Machine Repair",icon:"🫧", jobType:"repair",      visitFee:199,
        description:"Not spinning, leaking, making noise, not draining",            duration:"45-90 min" },
      { name:"Refrigerator / Fridge", icon:"🧊", jobType:"repair",      visitFee:199,
        description:"Not cooling, compressor issue, water leaking, ice not forming",duration:"45-90 min" },
      { name:"Microwave Repair",      icon:"📡", jobType:"repair",      visitFee:199,
        description:"Not heating, sparking, turntable issue, display problem",      duration:"30-60 min" },
      { name:"Water Heater / Geyser", icon:"🔥", jobType:"repair",      visitFee:199,
        description:"Not heating, leaking, pressure issue, pilot not lighting",     duration:"30-60 min" },
      { name:"RO Water Purifier",     icon:"💧", jobType:"repair",      visitFee:149,
        description:"Not purifying, low flow, leaking, TDS too high",              duration:"30-60 min" },
      { name:"Washing Machine Service",icon:"🧹", jobType:"maintenance", fixedPrice:699,
        description:"Annual service — drum clean, inlet filter, pump check",        duration:"60 min" },
      { name:"Geyser Annual Service", icon:"🔧", jobType:"maintenance", fixedPrice:499,
        description:"Check heating element, clean tank, safety valve test",         duration:"45 min" },
      { name:"RO Filter Change",      icon:"🔄", jobType:"maintenance", fixedPrice:799,
        description:"Replace RO membrane and pre-filters",                          duration:"45 min" },
    ],
  },

  // ── Home Security ── ALL 3 TYPES ──────────────────────────────────────────
  {
    id:"security", name:"Home Security", icon:"🔒",
    description:"CCTV, alarms, smart locks and security systems",
    availableTypes:["repair","maintenance","consultation"],
    services:[
      { name:"CCTV Camera Repair",   icon:"📷", jobType:"repair",      visitFee:199,
        description:"Camera not recording, offline, blurry, night vision issue",    duration:"30-60 min" },
      { name:"Lock Repair",          icon:"🔑", jobType:"repair",      visitFee:149,
        description:"Door lock broken, jammed, key stuck, lock cylinder damage",    duration:"20-45 min" },
      { name:"CCTV Annual Service",  icon:"🧹", jobType:"maintenance", fixedPrice:999,
        description:"Clean cameras, check recording, test alerts, update firmware", duration:"90 min" },
      { name:"Security Audit",       icon:"📋", jobType:"consultation", consultFee:599,
        description:"Expert assesses your home security and recommends cameras, alarms and locks", duration:"60 min" },
    ],
  },

  // ── Interior Design ── CONSULTATION ONLY ─────────────────────────────────
  {
    id:"interior_design", name:"Interior Design", icon:"🏡",
    description:"Expert advice for home design and renovation",
    availableTypes:["consultation"],  // ONLY consultation — no repair, no maintenance
    services:[
      { name:"Home Design Consultation",  icon:"🎨", jobType:"consultation", consultFee:999,
        description:"Interior designer visits and creates a mood board and cost plan", duration:"90 min" },
      { name:"Modular Kitchen Planning",  icon:"🍳", jobType:"consultation", consultFee:799,
        description:"Expert designs your modular kitchen layout with material estimate", duration:"90 min" },
      { name:"Wardrobe / Storage Design", icon:"🛋️", jobType:"consultation", consultFee:599,
        description:"Custom wardrobe or storage solution with 3D plan and cost",    duration:"60 min" },
    ],
  },

  // ── Waterproofing ── REPAIR + MAINTENANCE ─────────────────────────────────
  {
    id:"waterproofing", name:"Waterproofing & Seepage", icon:"💧",
    description:"Fix leaks, seepage and waterproofing for roof, bathroom and walls",
    availableTypes:["repair","maintenance"],
    services:[
      { name:"Roof / Terrace Leaking",  icon:"🏚️", jobType:"repair",      visitFee:249,
        description:"Water leaking through roof or terrace into rooms below",        duration:"2-4 hrs" },
      { name:"Bathroom Seepage",        icon:"🚿", jobType:"repair",      visitFee:249,
        description:"Water seeping through bathroom floor or walls to adjacent room",duration:"2-4 hrs" },
      { name:"Wall Seepage / Dampness", icon:"🧱", jobType:"repair",      visitFee:199,
        description:"Wet or damp walls, paint peeling due to moisture",             duration:"2-4 hrs" },
      { name:"Roof Waterproofing",      icon:"🏗️", jobType:"maintenance", fixedPrice:8999,
        description:"Preventive waterproofing coat for terrace/roof before monsoon",duration:"1-2 days" },
    ],
  },

];

// ── Helper functions ───────────────────────────────────────────────────────────
/** Get categories that support a specific job type */
export function categoriesForType(type: ServiceJobType): ServiceCategory[] {
  return SERVICE_CATEGORIES.filter(c => c.availableTypes.includes(type));
}

/** Get services from a category filtered by job type */
export function servicesForCategoryAndType(
  categoryId: string, type: ServiceJobType
): ServiceItem[] {
  const cat = SERVICE_CATEGORIES.find(c => c.id === categoryId);
  return (cat?.services ?? []).filter(s => s.jobType === type);
}

/** Get all services for a category (all types) */
export function allServicesForCategory(categoryId: string): ServiceItem[] {
  return SERVICE_CATEGORIES.find(c => c.id === categoryId)?.services ?? [];
}

/** Returns true if this category only has one job type available */
export function isSingleTypeCategory(categoryId: string): boolean {
  const cat = SERVICE_CATEGORIES.find(c => c.id === categoryId);
  return (cat?.availableTypes.length ?? 0) === 1;
}

/** Get the single type for a single-type category */
export function getSingleType(categoryId: string): ServiceJobType | null {
  const cat = SERVICE_CATEGORIES.find(c => c.id === categoryId);
  return cat?.availableTypes.length === 1 ? cat.availableTypes[0] : null;
}
