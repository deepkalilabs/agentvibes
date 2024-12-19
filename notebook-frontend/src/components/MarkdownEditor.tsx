'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import { MarkdownEditorProps } from '@/app/types';

const MonacoEditor = dynamic(
  () => import('@monaco-editor/react'),
  { ssr: false }
);


export function MarkdownEditor({ code, onCodeChange, isMarkdownEditing }: MarkdownEditorProps) {
  //const [isEditing, setIsEditing] = useState(false);
  const [isEditorReady, setIsEditorReady] = useState(false);

  const calculateEditorHeight = (value: string) => {
    const lineCount = value ? value.split("\n").length : 1;
    const baseHeight = 200;
    const lineHeight = 20;
    return Math.max(baseHeight, Math.min(lineCount * lineHeight, 500));
  };

  useEffect(() => {
    console.log(code);
    console.log(isEditorReady);
  }, [code]);

  return (
    <div className="w-full">
      {isMarkdownEditing ? (
        <MonacoEditor
          height={calculateEditorHeight(code)}
          language="markdown"
          value={code}
          onChange={(value) => onCodeChange(value || '')}
          onMount={() => setIsEditorReady(true)}
          options={{
            minimap: { enabled: false },
            lineNumbers: 'off',
            wordWrap: 'on',
            fontSize: 14,
            scrollBeyondLastLine: false,
          }}
        />
      ) : (
        <div className="prose prose-slate dark:prose-invert max-w-none">
          <ReactMarkdown>{code}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export default MarkdownEditor;