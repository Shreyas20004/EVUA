"use client"

import Header from '@/components/Header';
import StatsGrid from '@/components/StatsGrid';
import ProjectFiles from '@/components/ProjectFiles';
import CodeDiff from '@/components/CodeDiff';
import AssistantPanel from '@/components/AssistantPanel';
import FooterActions from '@/components/FooterActions';
import { useState } from 'react';
import { projectFiles, codeDiff } from '@/data/files';


export default function Home() {
  const [selectedFile, setSelectedFile] = useState('legacy/utils.py');


  return (
    <div className="min-h-screen bg-black text-white p-6">
      <Header />
      <StatsGrid />


      <div className="grid grid-cols-4 gap-4">
        <ProjectFiles selectedFile={selectedFile} setSelectedFile={setSelectedFile} />
        <CodeDiff codeDiff={codeDiff} />
        <AssistantPanel selectedFile={selectedFile} />
      </div>


      <FooterActions />
    </div>
  );
}