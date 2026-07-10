import React, {
  useState, useRef, useEffect, useCallback, memo,
} from "react";
import {
  Animated, Easing, FlatList, KeyboardAvoidingView,
  Platform, StyleSheet, Text, TextInput,
  TouchableOpacity, View, Dimensions,
} from "react-native";
import { useAction }  from "../hooks/useApi";
import { aiApi }      from "../lib/api";
import {
  LANG_LABELS, LOADING_PHRASES, BOT_GREETING,
  OPT_LABELS, BOOKING_MSG, SOMETHING_ELSE, INPUT_PLACEHOLDER,
  type Lang,
} from "../lib/i18n";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

const { width } = Dimensions.get("window");

// ── Decision tree (structure only — labels come from i18n) ────────────────────
const TREE: Record<string, { opts: { emoji: string; next: string }[] }> = {
  ac:             { opts:[{emoji:"🥵",next:"ac_how_long"},{emoji:"🔌",next:"book:ac:AC Not Switching On:repair:199"},{emoji:"💧",next:"book:ac:AC Water Leaking:repair:199"},{emoji:"🔊",next:"book:ac:AC Making Noise:repair:199"},{emoji:"🧹",next:"book:ac:AC Annual Service:maintenance:699"},{emoji:"🫧",next:"book:ac:AC Deep Cleaning:maintenance:1299"},{emoji:"💨",next:"book:ac:AC Gas Refill:maintenance:2499"},{emoji:"📋",next:"book:ac:AC Inspection Report:consultation:299"}] },
  ac_how_long:    { opts:[{emoji:"🕐",next:"book:ac:AC Not Cooling:repair:199"},{emoji:"📅",next:"book:ac:AC Not Cooling:repair:199"},{emoji:"📆",next:"book:ac:AC Not Cooling:repair:199"}] },
  plumbing:       { opts:[{emoji:"🚿",next:"book:plumbing:Pipe Leaking:repair:149"},{emoji:"🚰",next:"book:plumbing:Tap / Faucet Problem:repair:149"},{emoji:"🚫",next:"book:plumbing:Drain Blocked:repair:149"},{emoji:"🚾",next:"book:plumbing:Toilet Repair:repair:149"},{emoji:"💧",next:"book:plumbing:Water Tank Cleaning:maintenance:799"},{emoji:"🧹",next:"book:plumbing:Drain Cleaning:maintenance:599"},{emoji:"📋",next:"book:plumbing:Plumbing Assessment:consultation:299"}] },
  electrical:     { opts:[{emoji:"⚡",next:"book:electrical:No Power / Short Circuit:repair:199"},{emoji:"🔌",next:"book:electrical:Socket / Switch Repair:repair:149"},{emoji:"💡",next:"book:electrical:Fan / Light Not Working:repair:149"},{emoji:"🛡️",next:"book:electrical:Electrical Safety Audit:maintenance:499"},{emoji:"🏗️",next:"book:electrical:Electrical Home Audit:consultation:399"}] },
  cleaning:       { opts:[{emoji:"🏠",next:"book:cleaning:Home Deep Cleaning:maintenance:1999"},{emoji:"🍳",next:"book:cleaning:Kitchen Deep Clean:maintenance:1299"},{emoji:"🚿",next:"book:cleaning:Bathroom Deep Clean:maintenance:799"},{emoji:"🛋️",next:"book:cleaning:Sofa / Carpet Cleaning:maintenance:999"}] },
  pest_control:   { opts:[{emoji:"🪳",next:"book:pest_control:General Pest Control:maintenance:999"},{emoji:"🐭",next:"book:pest_control:Rodent Control:maintenance:1499"},{emoji:"🪲",next:"book:pest_control:Termite Treatment:maintenance:3999"},{emoji:"🛏️",next:"book:pest_control:Bed Bug Treatment:maintenance:2499"},{emoji:"📋",next:"book:pest_control:Pest Inspection Report:consultation:299"}] },
  appliances:     { opts:[{emoji:"🫧",next:"appliance_wm"},{emoji:"🧊",next:"book:appliances:Refrigerator / Fridge:repair:199"},{emoji:"📡",next:"book:appliances:Microwave Repair:repair:199"},{emoji:"🔥",next:"appliance_geyser"},{emoji:"💧",next:"book:appliances:RO Water Purifier:repair:149"}] },
  appliance_wm:   { opts:[{emoji:"🌀",next:"book:appliances:Washing Machine Repair:repair:199"},{emoji:"💧",next:"book:appliances:Washing Machine Repair:repair:199"},{emoji:"🧹",next:"book:appliances:Washing Machine Service:maintenance:699"}] },
  appliance_geyser:{ opts:[{emoji:"❄️",next:"book:appliances:Water Heater / Geyser:repair:199"},{emoji:"💧",next:"book:appliances:Water Heater / Geyser:repair:199"},{emoji:"🧹",next:"book:appliances:Geyser Annual Service:maintenance:499"}] },
  painting:       { opts:[{emoji:"🖼️",next:"book:painting:Single Room Painting:maintenance:4999"},{emoji:"🏠",next:"book:painting:Full Home Painting:maintenance:24999"},{emoji:"📄",next:"book:painting:Wallpaper Installation:maintenance:2999"},{emoji:"🎨",next:"book:painting:Painting Consultation:consultation:499"},{emoji:"🔍",next:"book:painting:Wall Crack / Seepage Consultation:consultation:399"}] },
  carpentry:      { opts:[{emoji:"🪑",next:"book:carpentry:Furniture Repair:repair:149"},{emoji:"🚪",next:"book:carpentry:Door / Window Problem:repair:149"},{emoji:"🔩",next:"book:carpentry:Furniture Assembly:maintenance:499"},{emoji:"📐",next:"book:carpentry:Renovation Consultation:consultation:599"}] },
  waterproofing:  { opts:[{emoji:"🏚️",next:"book:waterproofing:Roof / Terrace Leaking:repair:249"},{emoji:"🚿",next:"book:waterproofing:Bathroom Seepage:repair:249"},{emoji:"🧱",next:"book:waterproofing:Wall Seepage / Dampness:repair:199"},{emoji:"🛡️",next:"book:waterproofing:Roof Waterproofing:maintenance:8999"}] },
  interior_design:{ opts:[{emoji:"🏠",next:"book:interior_design:Home Design Consultation:consultation:999"},{emoji:"🍳",next:"book:interior_design:Modular Kitchen Planning:consultation:799"},{emoji:"🛋️",next:"book:interior_design:Wardrobe / Storage Design:consultation:599"}] },
};

const CAT_COLORS: Record<string,string> = {
  ac:"#0EA5E9", plumbing:"#3B82F6", electrical:"#F59E0B", cleaning:"#10B981",
  pest_control:"#8B5CF6", appliances:"#6366F1", painting:"#EC4899",
  carpentry:"#D97706", waterproofing:"#0284C7", interior_design:"#14B8A6",
};
const CAT_NAMES: Record<string,string> = {
  ac:"AC & Cooling", plumbing:"Plumbing", electrical:"Electrical",
  cleaning:"Cleaning", pest_control:"Pest Control", appliances:"Appliances",
  painting:"Painting", carpentry:"Carpentry", waterproofing:"Waterproofing",
  interior_design:"Interior Design",
};
const TYPE_INFO = {
  repair:       { icon:"🔧", color:"#DC2626", label:{ pa:"ਮੁਰੰਮਤ", hi:"मरम्मत",    en:"Repair"       }, bg:"#FFF0F0" },
  maintenance:  { icon:"⚙️", color:"#16A34A", label:{ pa:"ਸਰਵਿਸ",  hi:"सर्विस",    en:"Service"      }, bg:"#F0FDF4" },
  consultation: { icon:"📋", color:"#7C3AED", label:{ pa:"ਸਲਾਹ",    hi:"परामर्श",   en:"Consultation" }, bg:"#F5F3FF" },
};
const PRICE_SUFFIX = {
  repair:       { pa:"ਵਿਜ਼ਿਟ ਫ਼ੀਸ · ਜਾਂਚ ਤੋਂ ਬਾਅਦ ਪੂਰੀ ਕੀਮਤ",      hi:"विज़िट फ़ीस · जाँच के बाद पूरी कीमत",    en:"visit fee · full quote after inspection" },
  maintenance:  { pa:"ਫ਼ਿਕਸਡ ਕੀਮਤ · ਕੋਈ ਲੁਕਵੀਂ ਫ਼ੀਸ ਨਹੀਂ",        hi:"फ़िक्स्ड कीमत · कोई छुपी फ़ीस नहीं",     en:"fixed price · no hidden charges" },
  consultation: { pa:"ਸਲਾਹ ਫ਼ੀਸ · ਵਿਸਤਾਰਤ ਰਿਪੋਰਟ ਮਿਲੇਗੀ",         hi:"परामर्श फ़ीस · विस्तृत रिपोर्ट मिलेगी", en:"consult fee · detailed report included" },
};
const BOOK_NOW_LABEL = { pa:"ਹੁਣੇ ਬੁੱਕ ਕਰੋ →", hi:"अभी बुक करें →", en:"Book Now →" };
const APPROVE_NOTE   = { pa:"ਕੰਮ ਸ਼ੁਰੂ ਹੋਣ ਤੋਂ ਪਹਿਲਾਂ ਤੁਸੀਂ ਮਨਜ਼ੂਰੀ ਦਿਓਗੇ।", hi:"काम शुरू होने से पहले आप मंज़ूरी देंगे।", en:"You approve the full repair quote before any work begins." };

// ── Types ──────────────────────────────────────────────────────────────────────
interface Booking { category_id:string; service_name:string; job_type:"repair"|"maintenance"|"consultation"; price:number }
type MsgPhase = "shimmer"|"typing"|"done";
interface ChatMsg {
  id:string; role:"bot"|"user"; text:string;
  opts?:{ emoji:string; label:string; next:string }[];
  booking?:Booking|null; phase?:MsgPhase;
}

function buildBooking(next:string):Booking|null {
  if(!next.startsWith("book:"))return null;
  const[,c,n,t,p]=next.split(":"); return{category_id:c,service_name:n,job_type:t as Booking["job_type"],price:Number(p)};
}

// ── Shimmer component ──────────────────────────────────────────────────────────
const ShimmerRow = memo(({ w, delay, color }:{w:number;delay:number;color:string}) => {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(()=>{
    const loop = Animated.loop(
      Animated.sequence([
        Animated.delay(delay),
        Animated.timing(anim,{toValue:1,duration:900,easing:Easing.inOut(Easing.ease),useNativeDriver:true}),
        Animated.timing(anim,{toValue:0,duration:600,easing:Easing.ease,useNativeDriver:true}),
      ])
    );
    loop.start();
    return()=>loop.stop();
  },[]);
  const opacity = anim.interpolate({inputRange:[0,0.5,1],outputRange:[0.15,0.45,0.15]});
  return(
    <Animated.View style={{height:14,borderRadius:7,backgroundColor:color,opacity,width:w,marginBottom:8}}/>
  );
});

// ── Typing dots ────────────────────────────────────────────────────────────────
const TypingDots = memo(({color}:{color:string})=>{
  const dots=[useRef(new Animated.Value(0)).current,useRef(new Animated.Value(0)).current,useRef(new Animated.Value(0)).current];
  useEffect(()=>{
    const anims=dots.map((d,i)=>Animated.loop(Animated.sequence([
      Animated.delay(i*160),
      Animated.timing(d,{toValue:1,duration:300,useNativeDriver:true}),
      Animated.timing(d,{toValue:0,duration:300,useNativeDriver:true}),
      Animated.delay(320),
    ])));
    anims.forEach(a=>a.start());
    return()=>anims.forEach(a=>a.stop());
  },[]);
  return(
    <View style={{flexDirection:"row",gap:5,paddingHorizontal:4,paddingVertical:2}}>
      {dots.map((d,i)=>(
        <Animated.View key={i} style={{width:8,height:8,borderRadius:4,backgroundColor:color,
          opacity:d,transform:[{translateY:d.interpolate({inputRange:[0,1],outputRange:[0,-4]})}]}}/>
      ))}
    </View>
  );
});

// ── Typewriter text ────────────────────────────────────────────────────────────
const TypewriterText = memo(({ text, speed=22, color, onDone }:{text:string;speed?:number;color:string;onDone?:()=>void})=>{
  const [shown,setShown]=useState(0);
  useEffect(()=>{
    setShown(0);
    let i=0;
    const id=setInterval(()=>{ i++; setShown(i); if(i>=text.length){clearInterval(id);onDone?.();} },speed);
    return()=>clearInterval(id);
  },[text]);
  return <Text style={{fontSize:15,lineHeight:23,color}}>{text.slice(0,shown)}</Text>;
});

// ── Animated option button ─────────────────────────────────────────────────────
const AnimatedOption = memo(({label,emoji,delay,onPress,catColor,disabled}:{
  label:string;emoji:string;delay:number;onPress:()=>void;catColor:string;disabled:boolean;
})=>{
  const slide=useRef(new Animated.Value(40)).current;
  const fade=useRef(new Animated.Value(0)).current;
  useEffect(()=>{
    Animated.parallel([
      Animated.timing(fade,{toValue:1,duration:280,delay,easing:Easing.out(Easing.cubic),useNativeDriver:true}),
      Animated.spring(slide,{toValue:0,delay,tension:80,friction:10,useNativeDriver:true}),
    ]).start();
  },[]);
  return(
    <Animated.View style={{opacity:fade,transform:[{translateX:slide}]}}>
      <TouchableOpacity
        style={[s.optBtn,{borderColor:disabled?"#E2E8F0":catColor+"55",backgroundColor:disabled?"#F8FAFC":catColor+"08"}]}
        onPress={onPress} disabled={disabled} activeOpacity={0.72}>
        <Text style={{fontSize:18,width:28}}>{emoji}</Text>
        <Text style={[s.optLabel,{color:disabled?"#94A3B8":"#1E293B"}]}>{label}</Text>
      </TouchableOpacity>
    </Animated.View>
  );
});

// ── Cycling loading text ───────────────────────────────────────────────────────
const CyclingText = memo(({phrases,color}:{phrases:string[];color:string})=>{
  const [idx,setIdx]=useState(0);
  const fade=useRef(new Animated.Value(1)).current;
  useEffect(()=>{
    const id=setInterval(()=>{
      Animated.sequence([
        Animated.timing(fade,{toValue:0,duration:220,useNativeDriver:true}),
        Animated.timing(fade,{toValue:1,duration:220,useNativeDriver:true}),
      ]).start();
      setIdx(i=>(i+1)%phrases.length);
    },900);
    return()=>clearInterval(id);
  },[phrases]);
  return(
    <Animated.Text style={{opacity:fade,fontSize:12,color,fontStyle:"italic",marginTop:4}}>
      {phrases[idx]}
    </Animated.Text>
  );
});

// ── Main component ─────────────────────────────────────────────────────────────
type Params = { categoryId:string };
type Props  = NativeStackScreenProps<{SmartBot:Params},"SmartBot">;

export function SmartBotScreen({route,navigation}:Props){
  const {categoryId}=route.params;
  const catColor=CAT_COLORS[categoryId]??"#2563EB";
  const catName=CAT_NAMES[categoryId]??categoryId;

  const [lang,setLang]=useState<Lang>("pa"); // Punjabi first
  const [msgs,setMsgs]=useState<ChatMsg[]>([]);
  const [input,setInput]=useState("");
  const [history,setHistory]=useState<{role:string;content:string}[]>([]);
  const [usedOpts,setUsedOpts]=useState<Set<string>>(new Set());
  const [phase,setPhase]=useState<MsgPhase>("done");

  const listRef=useRef<FlatList>(null);
  const chatAction=useAction(useCallback((m:string,h:typeof history)=>aiApi.chat(m,h),[]));

  const phrases=LOADING_PHRASES[lang];

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function getNodeOpts(nodeId:string){
    const node=TREE[nodeId];
    if(!node)return[];
    const labels=OPT_LABELS[lang][nodeId]??[];
    return node.opts.map((o,i)=>({emoji:o.emoji,label:labels[i]??o.emoji,next:o.next}));
  }

  function deliverBotMsg(msg:Omit<ChatMsg,"id"|"phase">){
    const id=`b-${Date.now()}`;
    // 1. shimmer
    setPhase("shimmer");
    setMsgs(prev=>[...prev,{...msg,id,phase:"shimmer",opts:undefined,booking:undefined}]);
    scroll();
    // 2. typing dots
    setTimeout(()=>{
      setMsgs(prev=>prev.map(m=>m.id===id?{...m,phase:"typing"}:m));
      scroll();
    },750);
    // 3. done — typewriter runs inside renderMsg
    setTimeout(()=>{
      setMsgs(prev=>prev.map(m=>m.id===id?{...m,phase:"done",opts:msg.opts,booking:msg.booking}:m));
      setPhase("done");
      scroll();
    },1350);
  }

  function scroll(){setTimeout(()=>listRef.current?.scrollToEnd({animated:true}),120);}

  // ── Init ────────────────────────────────────────────────────────────────────
  useEffect(()=>{
    const q=BOT_GREETING[lang][categoryId]??"";
    const opts=getNodeOpts(categoryId);
    deliverBotMsg({role:"bot",text:q,opts:opts.length?opts:undefined});
  },[categoryId,lang]);

  // ── Option tap ──────────────────────────────────────────────────────────────
  function handleOption(label:string,emoji:string,next:string){
    const userMsg:ChatMsg={id:`u-${Date.now()}`,role:"user",text:`${emoji}  ${label}`,phase:"done"};
    setMsgs(prev=>[...prev,userMsg]);
    setUsedOpts(prev=>new Set([...prev,label]));
    const newH=[...history,{role:"user",content:label}];
    setHistory(newH);
    scroll();

    if(next.startsWith("book:")){
      const b=buildBooking(next)!;
      const priceLine=`₹${b.price.toLocaleString("en-IN")} ${PRICE_SUFFIX[b.job_type][lang]}`;
      const text=BOOKING_MSG[lang](b.service_name,priceLine);
      deliverBotMsg({role:"bot",text,booking:b});
    } else if(TREE[next]){
      const q=BOT_GREETING[lang][next]??(BOT_GREETING[lang][categoryId]??"");
      const opts=getNodeOpts(next);
      deliverBotMsg({role:"bot",text:q,opts});
    } else {
      callAI(label,newH);
    }
  }

  // ── AI fallback ─────────────────────────────────────────────────────────────
  async function callAI(msg:string,hist:typeof history){
    deliverBotMsg({role:"bot",text:""});
    const res=await chatAction.execute(`[${catName}] ${msg}`,hist);
    if(res?.reply){
      const clean=res.reply.replace(/<BOOK>[\s\S]*?<\/BOOK>/g,"").trim();
      setMsgs(prev=>{
        const last=[...prev].reverse().find(m=>m.role==="bot");
        if(!last)return prev;
        return prev.map(m=>m.id===last.id?{...m,text:clean,phase:"done"}:m);
      });
      setHistory([...hist,{role:"assistant",content:res.reply}]);
    }
  }

  async function handleSend(){
    const msg=input.trim(); if(!msg)return;
    setInput("");
    const userMsg:ChatMsg={id:`u-${Date.now()}`,role:"user",text:msg,phase:"done"};
    setMsgs(prev=>[...prev,userMsg]);
    const newH=[...history,{role:"user",content:msg}];
    setHistory(newH);
    await callAI(msg,newH);
  }

  function handleBook(b:Booking){
    navigation.navigate("BookService" as never,{categoryId:b.category_id,preselectedService:b.service_name,jobType:b.job_type} as never);
  }

  // ── Render message ──────────────────────────────────────────────────────────
  function renderMsg({item:m}:{item:ChatMsg}){
    const isUser=m.role==="user";

    if(isUser){
      return(
        <View style={[s.row,s.rowUser]}>
          <View style={[s.userBubble,{backgroundColor:catColor}]}>
            <Text style={s.userBubbleText}>{m.text}</Text>
          </View>
        </View>
      );
    }

    // ── Bot bubble ─────────────────────────────────────────────────────────
    return(
      <View style={s.botRow}>
        <View style={[s.avatarWrap,{backgroundColor:catColor+"18"}]}>
          <Text style={{fontSize:17}}>🤖</Text>
        </View>
        <View style={s.botContent}>

          {/* Shimmer phase */}
          {m.phase==="shimmer"&&(
            <View style={[s.botBubble,{gap:4,paddingBottom:14}]}>
              <ShimmerRow w={width*0.45} delay={0}   color={catColor}/>
              <ShimmerRow w={width*0.32} delay={120} color={catColor}/>
              <ShimmerRow w={width*0.38} delay={240} color={catColor}/>
              <CyclingText phrases={phrases} color={catColor}/>
            </View>
          )}

          {/* Typing phase */}
          {m.phase==="typing"&&(
            <View style={s.botBubble}>
              <TypingDots color={catColor}/>
            </View>
          )}

          {/* Done phase */}
          {m.phase==="done"&&m.text!=""&&(
            <View style={s.botBubble}>
              <TypewriterText text={m.text.replace(/\*\*/g,"")} color="#1E293B"
                onDone={()=>scroll()}/>
            </View>
          )}

          {/* Options — appear after typewriter */}
          {m.phase==="done"&&m.opts&&(
            <View style={s.optsWrap}>
              {m.opts.map((o,i)=>(
                <AnimatedOption key={o.label} label={o.label} emoji={o.emoji}
                  delay={i*70} catColor={catColor}
                  disabled={usedOpts.has(o.label)||phase==="shimmer"||phase==="typing"}
                  onPress={()=>handleOption(o.label,o.emoji,o.next)}/>
              ))}
              {/* "Something else" escape */}
              <AnimatedOption label={SOMETHING_ELSE[lang]} emoji=""
                delay={m.opts.length*70+80} catColor="#94A3B8" disabled={false}
                onPress={()=>{
                  setMsgs(prev=>prev.map(x=>x.id===m.id?{...x,opts:undefined}:x));
                }}/>
            </View>
          )}

          {/* Booking card */}
          {m.phase==="done"&&m.booking&&(()=>{
            const b=m.booking!;
            const t=TYPE_INFO[b.job_type];
            const lbl=t.label[lang];
            return(
              <Animated.View style={[s.bookCard,{borderColor:t.color+"44",backgroundColor:t.bg}]}>
                <View style={[s.bookHeader,{backgroundColor:t.color}]}>
                  <Text style={s.bookHeaderText}>{t.icon}  {lbl}</Text>
                </View>
                <View style={s.bookBody}>
                  <Text style={s.bookName}>{b.service_name}</Text>
                  <Text style={s.bookPrice}>
                    ₹{b.price.toLocaleString("en-IN")}
                    {"  ·  "}{PRICE_SUFFIX[b.job_type][lang]}
                  </Text>
                  {b.job_type==="repair"&&(
                    <Text style={s.bookNote}>{APPROVE_NOTE[lang]}</Text>
                  )}
                  <TouchableOpacity
                    style={[s.bookBtn,{backgroundColor:t.color}]}
                    onPress={()=>handleBook(b)} activeOpacity={0.85}>
                    <Text style={s.bookBtnText}>{BOOK_NOW_LABEL[lang]}</Text>
                  </TouchableOpacity>
                </View>
              </Animated.View>
            );
          })()}
        </View>
      </View>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return(
    <KeyboardAvoidingView style={s.screen}
      behavior={Platform.OS==="ios"?"padding":"height"} keyboardVerticalOffset={0}>

      {/* Header */}
      <View style={[s.header,{backgroundColor:catColor}]}>
        <TouchableOpacity onPress={()=>navigation.goBack()} style={s.backBtn}>
          <Text style={s.backArrow}>←</Text>
        </TouchableOpacity>
        <View style={s.headerCenter}>
          <Text style={s.headerTitle}>{catName}</Text>
          <Text style={s.headerSub}>🤖 ਸਮਾਰਟ ਅਸਿਸਟੈਂਟ</Text>
        </View>
        {/* Language toggle */}
        <View style={s.langBar}>
          {(["pa","hi","en"] as Lang[]).map(l=>(
            <TouchableOpacity key={l} onPress={()=>setLang(l)}
              style={[s.langBtn,lang===l&&{backgroundColor:"rgba(255,255,255,0.3)"}]}>
              <Text style={[s.langBtnText,lang===l&&{fontWeight:"800"}]}>
                {l==="pa"?"ਪੰ":l==="hi"?"हि":"EN"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <FlatList
        ref={listRef}
        data={msgs}
        keyExtractor={m=>m.id}
        renderItem={renderMsg}
        contentContainerStyle={s.list}
        showsVerticalScrollIndicator={false}
      />

      {/* Input */}
      <View style={s.inputBar}>
        <TextInput style={s.input} value={input} onChangeText={setInput}
          placeholder={INPUT_PLACEHOLDER[lang]}
          placeholderTextColor="#94A3B8" multiline maxLength={400}
          returnKeyType="send" onSubmitEditing={handleSend}/>
        <TouchableOpacity
          style={[s.sendBtn,{backgroundColor:input.trim()?catColor:"#E2E8F0"}]}
          onPress={handleSend} disabled={!input.trim()||chatAction.loading}
          activeOpacity={0.85}>
          <Text style={[s.sendIcon,{color:input.trim()?"#fff":"#94A3B8"}]}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────
const s=StyleSheet.create({
  screen:         {flex:1,backgroundColor:"#F0F4F8"},
  header:         {paddingTop:52,paddingBottom:14,paddingHorizontal:16,
                    flexDirection:"row",alignItems:"center",gap:10},
  backBtn:        {width:36,height:36,borderRadius:18,
                    backgroundColor:"rgba(255,255,255,0.2)",
                    alignItems:"center",justifyContent:"center"},
  backArrow:      {fontSize:20,color:"#fff",fontWeight:"700"},
  headerCenter:   {flex:1},
  headerTitle:    {fontSize:17,fontWeight:"800",color:"#fff",letterSpacing:-0.2},
  headerSub:      {fontSize:11,color:"rgba(255,255,255,0.75)",marginTop:1},
  langBar:        {flexDirection:"row",gap:2},
  langBtn:        {paddingHorizontal:8,paddingVertical:5,borderRadius:8},
  langBtnText:    {fontSize:12,color:"rgba(255,255,255,0.85)",fontWeight:"600"},
  list:           {padding:16,gap:14,paddingBottom:12},
  // User
  row:            {flexDirection:"row",justifyContent:"flex-end"},
  rowUser:        {justifyContent:"flex-end"},
  userBubble:     {maxWidth:"78%",borderRadius:18,borderBottomRightRadius:4,
                    paddingHorizontal:14,paddingVertical:11},
  userBubbleText: {fontSize:15,color:"#fff",lineHeight:22},
  // Bot
  botRow:         {flexDirection:"row",gap:10,alignItems:"flex-start"},
  avatarWrap:     {width:36,height:36,borderRadius:18,
                    alignItems:"center",justifyContent:"center",flexShrink:0,marginTop:4},
  botContent:     {flex:1,gap:10,maxWidth:width-80},
  botBubble:      {backgroundColor:"#fff",borderRadius:18,borderBottomLeftRadius:4,
                    paddingHorizontal:14,paddingVertical:13,
                    shadowColor:"#000",shadowOffset:{width:0,height:1},
                    shadowOpacity:0.07,shadowRadius:5,elevation:2},
  // Options
  optsWrap:       {gap:8,paddingLeft:2},
  optBtn:         {flexDirection:"row",alignItems:"center",gap:12,
                    paddingHorizontal:14,paddingVertical:13,borderRadius:14,
                    borderWidth:1.5,backgroundColor:"#fff",
                    shadowColor:"#000",shadowOffset:{width:0,height:1},
                    shadowOpacity:0.05,shadowRadius:3,elevation:1},
  optLabel:       {fontSize:14,fontWeight:"600",flex:1,lineHeight:20},
  // Booking card
  bookCard:       {borderRadius:18,borderWidth:1.5,overflow:"hidden",
                    shadowColor:"#000",shadowOffset:{width:0,height:4},
                    shadowOpacity:0.12,shadowRadius:10,elevation:5},
  bookHeader:     {paddingHorizontal:16,paddingVertical:10},
  bookHeaderText: {fontSize:13,fontWeight:"700",color:"#fff",
                    textTransform:"uppercase",letterSpacing:0.6},
  bookName:       {fontSize:18,fontWeight:"800",color:"#1E293B",marginBottom:6},
  bookPrice:      {fontSize:13,color:"#475569",lineHeight:20,marginBottom:6},
  bookNote:       {fontSize:12,color:"#64748B",fontStyle:"italic",
                    lineHeight:18,marginBottom:10},
  bookBody:       {padding:16,gap:2},
  bookBtn:        {borderRadius:12,paddingVertical:14,
                    alignItems:"center",marginTop:6},
  bookBtnText:    {fontSize:16,fontWeight:"800",color:"#fff",letterSpacing:-0.2},
  // Input
  inputBar:       {flexDirection:"row",gap:10,padding:12,paddingBottom:28,
                    alignItems:"flex-end",backgroundColor:"#fff",
                    borderTopWidth:1,borderTopColor:"#F1F5F9"},
  input:          {flex:1,minHeight:44,maxHeight:100,borderRadius:14,
                    borderWidth:1.5,borderColor:"#E2E8F0",
                    paddingHorizontal:14,paddingVertical:10,
                    fontSize:15,color:"#1E293B",backgroundColor:"#F8FAFC"},
  sendBtn:        {width:44,height:44,borderRadius:22,
                    alignItems:"center",justifyContent:"center"},
  sendIcon:       {fontSize:20,fontWeight:"800"},
});
