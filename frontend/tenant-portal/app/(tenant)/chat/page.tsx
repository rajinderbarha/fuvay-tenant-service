"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Btn, Avatar, Skeleton, Input, SectionHeader, Badge } from "../../../components/shared/ui";
import { chatApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
export default function ChatPage() {
  const [activeRoom, setActiveRoom] = useState<string|null>(null);
  const [msgText, setMsgText]       = useState("");
  const rooms    = useApi(useCallback(() => chatApi.listRooms(20),               []));
  const messages = useApi(useCallback(() => activeRoom ? chatApi.getMessages(activeRoom, 30) : Promise.resolve({ messages:[], has_next:false }), [activeRoom]));
  const sendAction = useAction(useCallback((roomId:string, text:string) => chatApi.sendMessage(roomId, text), []));
  async function handleSend() {
    if(!activeRoom||!msgText.trim())return;
    const res = await sendAction.execute(activeRoom, msgText.trim());
    if(res) { messages.refetch(); setMsgText(""); }
  }
  return <TenantLayout activeNav="chat">
    <SectionHeader title="Chat" subtitle="Customer conversations per job"/>
    <div style={{display:"grid",gridTemplateColumns:"280px 1fr",gap:16,height:560}}>
      {/* Room list */}
      <Card padding={0} style={{overflow:"hidden",display:"flex",flexDirection:"column"}}>
        <div style={{padding:"12px 16px",borderBottom:"1px solid var(--border)"}}>
          <p style={{fontSize:12,fontWeight:700,color:"var(--text-tertiary)",textTransform:"uppercase",letterSpacing:"0.06em",margin:0}}>Conversations</p>
        </div>
        <div style={{flex:1,overflowY:"auto"}}>
          {rooms.loading ? [...Array(4)].map((_,i)=><div key={i} style={{padding:"10px 16px"}}><Skeleton height={40}/></div>) :
          (rooms.data?.rooms ?? []).map(r=>(
            <div key={r.room_id} onClick={()=>setActiveRoom(r.room_id)}
              style={{display:"flex",alignItems:"center",gap:10,padding:"10px 16px",cursor:"pointer",
                background:activeRoom===r.room_id?"var(--accent-muted)":"transparent",
                borderBottom:"1px solid var(--border)"}}
              onMouseEnter={e=>{if(activeRoom!==r.room_id)(e.currentTarget as HTMLDivElement).style.background="var(--surface-sunken)"}}
              onMouseLeave={e=>{if(activeRoom!==r.room_id)(e.currentTarget as HTMLDivElement).style.background="transparent"}}>
              <Avatar name={r.participant_name} size={32}/>
              <div style={{flex:1,minWidth:0}}>
                <p style={{fontSize:12,fontWeight:600,color:"var(--text-primary)",margin:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.participant_name}</p>
                <p style={{fontSize:11,color:"var(--text-tertiary)",margin:"2px 0 0",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.last_message??r.job_number}</p>
              </div>
              {r.unread_count>0&&<Badge variant="danger" size="sm">{r.unread_count}</Badge>}
            </div>
          ))}
        </div>
      </Card>
      {/* Messages */}
      <Card padding={0} style={{display:"flex",flexDirection:"column",overflow:"hidden"}}>
        {!activeRoom ? (
          <div style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center"}}>
            <p style={{color:"var(--text-tertiary)",fontSize:13}}>Select a conversation</p>
          </div>
        ) : <>
          <div style={{flex:1,overflowY:"auto",padding:16,display:"flex",flexDirection:"column",gap:10}}>
            {messages.loading ? [...Array(5)].map((_,i)=><Skeleton key={i} height={40}/>)
            : (messages.data?.messages ?? []).map(msg=>(
              <div key={msg.message_id} style={{display:"flex",flexDirection:"column",alignItems:msg.sender_id===msg.room_id?"flex-start":"flex-end"}}>
                <div style={{maxWidth:"70%",padding:"8px 12px",borderRadius:"var(--radius-lg)",
                  background:msg.sender_id===msg.room_id?"var(--surface-sunken)":"var(--brand)",
                  color:msg.sender_id===msg.room_id?"var(--text-primary)":"white"}}>
                  <p style={{fontSize:13,margin:0}}>{msg.content}</p>
                </div>
                <p style={{fontSize:10,color:"var(--text-tertiary)",margin:"3px 6px 0"}}>{new Date(msg.sent_at).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}</p>
              </div>
            ))}
          </div>
          <div style={{padding:12,borderTop:"1px solid var(--border)",display:"flex",gap:8}}>
            <div style={{flex:1}}><Input placeholder="Type a message..." value={msgText} onChange={setMsgText}/></div>
            <Btn variant="primary" size="md" loading={sendAction.loading} onClick={handleSend}>Send</Btn>
          </div>
        </>}
      </Card>
    </div>
  </TenantLayout>;
}
