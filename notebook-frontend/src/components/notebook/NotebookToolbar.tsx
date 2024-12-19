// components/NotebookToolbar.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { PlusCircle } from 'lucide-react';
import { ShowCodeButton } from './toolbar/ShowCodeButton';
import { SaveNotebookButton } from './toolbar/SaveNotebookButton';
//import { LoadNotebookButton } from './toolbar/LoadNotebookButton';
import { DeployButton } from './toolbar/DeployButton';
import { RestartKernelButton } from './toolbar/RestartKernelButton';
import { CellType, NotebookToolbarProps } from '@/app/types';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

//TODO: Add name and description to the toolbar
export function NotebookToolbar({
  name,
  onHandleAddCell,
  onHandleSave,
  //onHandleLoad,
  onHandleRestartKernel,
  isConnected,
  allCells,
  onHandleDeploy,
}: NotebookToolbarProps) {

  const [ isAddCellOpen, setIsAddCellOpen ] = useState(false);
  const [ selectedCellType, setSelectedCellType ] = useState('code');

  const handleAddCell = () => {
    onHandleAddCell(selectedCellType as CellType);
    setIsAddCellOpen(false);
  }

  return (
    <div className="flex items-center space-x-2 mb-4">
      <div className="flex items-center gap-6 px-4 py-2 bg-muted rounded-lg text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <span className="font-medium">Name:</span>
          <span className="text-foreground">{name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium">Status:</span>
          <div className="flex items-center gap-1.5">
            <span className={`inline-flex h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span className="text-xs">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      <AlertDialog open={isAddCellOpen} onOpenChange={setIsAddCellOpen}>
        <AlertDialogTrigger asChild>
          <Button className="gap-2">
            <PlusCircle className="h-4 w-4" />
            Add Cell
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Select Cell Type</AlertDialogTitle>
          </AlertDialogHeader>
          <RadioGroup 
            value={selectedCellType} 
            onValueChange={(value) => setSelectedCellType(value as CellType)}
            className="grid gap-4"
          >
            <div className="flex items-center space-x-2 space-y-0">
              <RadioGroupItem value="code" id="code" />
              <Label htmlFor="code" className="flex items-center gap-2 cursor-pointer">
                <div className="h-4 w-4" />
                Code Cell
                <span className="text-sm text-muted-foreground">
                  - Execute code and see results
                </span>
              </Label>
            </div>
            <div className="flex items-center space-x-2 space-y-0">
              <RadioGroupItem value="markdown" id="markdown" />
              <Label htmlFor="markdown" className="flex items-center gap-2 cursor-pointer">
                <div className="h-4 w-4" />
                Markdown Cell
                <span className="text-sm text-muted-foreground">
                  - Write formatted text and documentation
                </span>
              </Label>
            </div>
            <div className="flex items-center space-x-2 space-y-0">
              <RadioGroupItem value="file" id="file" />
              <Label htmlFor="file" className="flex items-center gap-2 cursor-pointer">
                <div className="h-4 w-4" />
                File Upload Cell
                <span className="text-sm text-muted-foreground">
                  - Upload and process files
                </span>
              </Label>
            </div>
          </RadioGroup>
          <div className="flex justify-end gap-2 mt-6">
            <Button variant="outline" onClick={() => setIsAddCellOpen(false)}>Cancel</Button>
            <Button onClick={handleAddCell}>Add Selected Cell</Button>
          </div>
        </AlertDialogContent>
      </AlertDialog>

      <SaveNotebookButton onHandleSave={onHandleSave} />

      <ShowCodeButton allCells={allCells} />
      
      <RestartKernelButton 
        onHandleRestartKernel={onHandleRestartKernel}
        isConnected={isConnected}
      />

      <DeployButton 
        onDeploy={onHandleDeploy}
        isConnected={isConnected}
        disabled={allCells.length === 0}
      />

      {!isConnected && (
        <div className="text-sm text-muted-foreground">
          Not connected to kernel
        </div>
      )}
    </div>
  );
}