import React, { useState } from "react";
import { ScrollView, StyleSheet } from "react-native";
import { theme, gs } from "../../styles/theme";
import { JobNoteComposer } from "../../components/ux05/JobNoteComposer";
import { MediaCaptureGrid } from "../../components/ux05/MediaCaptureGrid";
import type { JobNoteView, JobMediaView } from "../../types/ux05";

const INITIAL_NOTES: JobNoteView[] = [
  { meta:{readiness:"mock_design_only"}, id:"n1", authorRole:"technician", visibility:"technician",
    text:"Filter was heavily clogged, replaced.", createdAt:"2026-07-18 10:05" },
];

export function JobNotesMediaShowcaseScreen() {
  const [notes, setNotes] = useState(INITIAL_NOTES);
  const [media, setMedia] = useState<JobMediaView[]>([]);

  function addNote(text: string, visibility: JobNoteView["visibility"]) {
    setNotes(prev => [...prev, {
      meta:{readiness:"mock_design_only"}, id:`n_${Date.now()}`, authorRole:"technician",
      visibility, text, createdAt:new Date().toISOString().slice(0,16).replace("T"," "),
    }]);
  }

  function addMedia() {
    setMedia(prev => [...prev, {
      meta:{readiness:"mock_design_only"}, id:`m_${Date.now()}`, localUri:null,
      uploadState:"draft", visibility:"internal", confirmedByBackend:false,
    }]);
  }

  function removeMedia(id: string) { setMedia(prev => prev.filter(m => m.id !== id)); }

  return (
    <ScrollView style={gs.screen} contentContainerStyle={s.content} testID="job-notes-media-showcase">
      <JobNoteComposer notes={notes} onAdd={addNote} />
      <MediaCaptureGrid items={media} onAdd={addMedia} onRemove={removeMedia} />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding:theme.spacing.base, gap:12, paddingBottom:32 },
});
