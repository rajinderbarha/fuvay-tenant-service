import React, { useCallback, useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useAction } from "../hooks/useApi";
import { reviewsApi } from "../lib/api";
import { StarRating } from "../components/StarRating";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { theme, gs } from "../styles/theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

type Params = { bookingId:string; jobId?:string };
type Props  = NativeStackScreenProps<{ Review:Params }, "Review">;

const PROMPT_LABELS: [number,string][] = [
  [1,"Very dissatisfied 😞"],[2,"Dissatisfied 😕"],[3,"Okay 😐"],[4,"Satisfied 😊"],[5,"Excellent! 🌟"]
];

const TAGS = ["On time","Professional","Quality work","Clean","Friendly","Thorough"];

export function ReviewScreen({ route, navigation }: Props) {
  const { bookingId, jobId } = route.params;
  const [score,    setScore]    = useState(0);
  const [comment,  setComment]  = useState("");
  const [selTags,  setSelTags]  = useState<string[]>([]);
  const [submitted,setSubmitted]= useState(false);

  const submitAction = useAction(useCallback(
    (sc:number, cm:string) => reviewsApi.submit(jobId ?? bookingId, sc, cm), [jobId, bookingId]
  ));

  function toggleTag(tag:string) {
    setSelTags(prev => prev.includes(tag) ? prev.filter(t=>t!==tag) : [...prev,tag]);
  }

  async function handleSubmit() {
    if (score === 0) { Alert.alert("Rating Required","Please select a star rating."); return; }
    const fullComment = [selTags.join(", "), comment].filter(Boolean).join(". ");
    const res = await submitAction.execute(score, fullComment);
    if (res) setSubmitted(true);
  }

  if (submitted) return (
    <View style={[gs.screen,{ alignItems:"center", justifyContent:"center", padding:32, gap:16 }]}>
      <Text style={{ fontSize:64 }}>🌟</Text>
      <Text style={{ fontSize:theme.font.size.xxxl, fontWeight:"800", color:theme.colors.textPrimary, textAlign:"center" }}>
        Thank you!
      </Text>
      <Text style={{ fontSize:theme.font.size.base, color:theme.colors.textSecondary, textAlign:"center" }}>
        Your review helps us improve our service quality.
      </Text>
      <Button label="Back to Home" variant="primary" size="lg" fullWidth
        onPress={()=>navigation.navigate("Home" as never)}/>
    </View>
  );

  return (
    <KeyboardAvoidingView style={gs.screen} behavior={Platform.OS==="ios"?"padding":"height"}>
      <ScrollView contentContainerStyle={s.content}>
        {/* Star rating */}
        <Card style={{ alignItems:"center", gap:16, paddingVertical:24 }}>
          <Text style={s.ratingTitle}>How was your experience?</Text>
          <StarRating value={score} onChange={setScore} size={40}/>
          {score > 0 && (
            <Text style={s.ratingLabel}>{PROMPT_LABELS.find(([n])=>n===score)?.[1]}</Text>
          )}
        </Card>

        {/* Quick tags */}
        {score >= 4 && (
          <Card style={{ gap:12 }}>
            <Text style={gs.label}>What did you like?</Text>
            <View style={{ flexDirection:"row", flexWrap:"wrap", gap:8 }}>
              {TAGS.map(tag => (
                <View key={tag} onTouchEnd={()=>toggleTag(tag)}
                  style={[s.tag, selTags.includes(tag)&&s.tagActive]}>
                  <Text style={[s.tagText, selTags.includes(tag)&&s.tagTextActive]}>
                    {selTags.includes(tag)?"✓ ":""}{tag}
                  </Text>
                </View>
              ))}
            </View>
          </Card>
        )}

        {/* Comment */}
        <Card style={{ gap:10 }}>
          <Text style={gs.label}>Additional Comments</Text>
          <TextInput style={s.textarea} value={comment} onChangeText={setComment}
            placeholder="Tell us more about your experience…"
            placeholderTextColor={theme.colors.textTertiary}
            multiline numberOfLines={5} textAlignVertical="top"/>
        </Card>

        {submitAction.error && (
          <View style={s.errBox}><Text style={s.errText}>{submitAction.error}</Text></View>
        )}

        <Button label="Submit Review" variant="primary" size="lg"
          loading={submitAction.loading} disabled={score===0}
          onPress={handleSubmit} fullWidth/>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  content:      { padding:theme.spacing.base, gap:14, paddingBottom:40 },
  ratingTitle:  { fontSize:theme.font.size.xl, fontWeight:"700", color:theme.colors.textPrimary, textAlign:"center" },
  ratingLabel:  { fontSize:theme.font.size.lg, color:theme.colors.textSecondary },
  tag:          { paddingHorizontal:14, paddingVertical:8, borderRadius:theme.radius.full,
                  borderWidth:1, borderColor:theme.colors.border, backgroundColor:theme.colors.surfaceSunken },
  tagActive:    { borderColor:theme.colors.brand, backgroundColor:theme.colors.brand },
  tagText:      { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textSecondary },
  tagTextActive:{ color:"#fff" },
  textarea:     { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.lg,
                  padding:12, fontSize:theme.font.size.base, color:theme.colors.textPrimary,
                  minHeight:110, backgroundColor:theme.colors.surfaceSunken },
  errBox:       { backgroundColor:theme.colors.dangerBg, borderRadius:theme.radius.md,
                  padding:12, borderWidth:1, borderColor:theme.colors.dangerBorder },
  errText:      { fontSize:theme.font.size.sm, color:theme.colors.dangerText },
});
