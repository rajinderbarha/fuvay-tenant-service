import React, { useState } from "react";
import { ScrollView, StyleSheet, Text } from "react-native";
import { theme, gs } from "../../styles/theme";
import { InspectionForm } from "../../components/ux05/InspectionForm";
import { ChecklistSection, ChecklistProgress } from "../../components/ux05/ChecklistSection";
import { computeProgress, canComplete } from "../../lib/ux05/checklist";
import { Button } from "../../components/Button";
import type { InspectionDraftView, ChecklistExecutionView } from "../../types/ux05";

const INITIAL_INSPECTION: InspectionDraftView = {
  meta:{readiness:"mock_design_only"}, jobId:"sj_9f21ac", customerIssue:"AC not cooling",
  observations:"", recommendedWork:"", requiredParts:[], photos:[],
  customerVisibleSummary:"", internalNote:"", status:"draft",
};

const INITIAL_CHECKLIST: ChecklistExecutionView = {
  meta:{readiness:"mock_design_only"}, jobId:"sj_9f21ac", status:"in_progress", progressPercent:0,
  sections:[
    { title:"Safety Checks", items:[
      { id:"s1", label:"Power isolated before service", required:true, responseType:"pass_fail", value:null, photoAttached:false },
      { id:"s2", label:"Work area photo", required:true, responseType:"photo", value:null, photoAttached:false },
    ] },
    { title:"Diagnostics", items:[
      { id:"d1", label:"Refrigerant pressure (psi)", required:true, responseType:"numeric", value:null, photoAttached:false },
      { id:"d2", label:"Additional notes", required:false, responseType:"text", value:null, photoAttached:false },
    ] },
  ],
};

/** DEV-ONLY. API_CONTRACT_REQUIRED for both inspection and checklist content -- see backend-contract-blockers.md. */
export function InspectionChecklistShowcaseScreen() {
  const [inspection, setInspection] = useState(INITIAL_INSPECTION);
  const [checklist, setChecklist] = useState(INITIAL_CHECKLIST);
  const progress = computeProgress(checklist);
  const readyToComplete = canComplete(checklist);

  function updateInspection(field: keyof InspectionDraftView, value: string) {
    setInspection(prev => ({ ...prev, [field]: value, status: "draft" }));
  }

  function updateChecklistItem(itemId: string, value: string) {
    setChecklist(prev => ({
      ...prev,
      sections: prev.sections.map(sec => ({
        ...sec, items: sec.items.map(i => i.id === itemId ? { ...i, value } : i),
      })),
    }));
  }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="inspection-checklist-showcase">
      <Text style={gs.label}>Inspection (draft)</Text>
      <InspectionForm draft={inspection} onChange={updateInspection} readOnly={false} />

      <Text style={[gs.label, { marginTop:8 }]}>Checklist</Text>
      <ChecklistProgress percent={progress} />
      {checklist.sections.map(sec => (
        <ChecklistSection key={sec.title} section={sec} onChange={updateChecklistItem} />
      ))}
      <Button label={readyToComplete ? "Complete Checklist" : "Complete required items first"}
        variant={readyToComplete ? "success" : "secondary"} disabled={!readyToComplete} fullWidth
        onPress={() => setChecklist(prev => ({ ...prev, status:"complete" }))} />
      <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live inspection/checklist-content endpoint exists yet.</Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content:  { padding:theme.spacing.base, gap:12, paddingBottom:32 },
  mockNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary, textAlign:"center" },
});
