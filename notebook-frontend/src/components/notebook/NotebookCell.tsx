'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Loader2, ChevronUp, ChevronDown, Trash2 } from 'lucide-react';
import { NotebookCellProps } from '@/app/types';
import { CodeEditor } from '@/components/CodeEditor';
import { MarkdownEditor } from '@/components/MarkdownEditor';
import { Edit, Eye } from 'lucide-react';
import { FileUploadEditor } from "@/components/FileUpload";

//type CellType = 'code' | 'markdown' | 'file';

// TODO: Break up notebook cell into different classes all extending from base notebookcell class.

export function NotebookCell({
  //id,
  code,
  output,
  type,
  executionCount,
  isExecuting,
  onCodeChange,
  //onFilesChange,
  onExecute,
  onDelete,
  onMoveUp,
  onMoveDown
}: NotebookCellProps) {
  const [isMarkdownEditing, setIsMarkdownEditing] = useState(false);

  const renderCellContent = () => {
    switch (type) {
      case 'markdown':
        return (
          <MarkdownEditor 
            code={code || ""} 
            onCodeChange={onCodeChange} 
            isMarkdownEditing={isMarkdownEditing}
          />
        );

      case 'file':
        return (
          <FileUploadEditor
          />
        );

      case 'code':
      default:
        return (
          <CodeEditor
            code={code || ""}
            output={output}
            executionCount={executionCount}
            onCodeChange={onCodeChange}
          />
        );
    }
  };

  return (
    <Card className="group min-h-[25vh] max-h-[75vh] h-auto overflow-auto">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 sticky top-0 z-50 bg-background py-2 border-b">
        <div className="flex flex-row items-center space-x-2">
          {type === 'code' && (
            <Button
              size="sm"
              onClick={onExecute}
              disabled={isExecuting}
              className="flex items-center"
              variant="default"
            >
              {isExecuting ? (
                <div className="flex items-center">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </div>
              ) : (
                'Run'
              )}
            </Button>
          )}

          {type === 'markdown' && (
              <Button
                size="sm"
                variant="default"
                className="flex items-center"
                onClick={() => setIsMarkdownEditing(!isMarkdownEditing)}
              >
                {isMarkdownEditing ? <Eye className="h-4 w-4" /> : <Edit className="h-4 w-4" />}
              </Button>
          )}
          
          <div className="flex flex-row items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              size="sm"
              variant="default"
              onClick={onMoveUp}
            >
              <ChevronUp className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="default"
              onClick={onMoveDown}
            >
              <ChevronDown className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="default"
              onClick={onDelete}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <div className="text-sm text-muted-foreground">
          {type === 'code' && (executionCount > 0 ? `In [${executionCount}]` : 'In [ ]')}
          {type === 'markdown' && 'Markdown'}
          {type === 'file' && 'File Upload'}
        </div>
      </CardHeader>
      
      <CardContent>
        {renderCellContent()}
      </CardContent>
    </Card>
  );
}

export default NotebookCell;