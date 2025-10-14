import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';


export default function AssistantPanel({ selectedFile }) {
    return (
        <Card className="bg-zinc-900 border-zinc-800 col-span-1">
            <CardContent className="p-4">
                <h3 className="text-lg font-semibold mb-4">Assistant</h3>
                <div className="text-sm text-zinc-400 mb-3">
                    Context: <span className="text-white">{selectedFile}</span> • Mode: <span className="text-white">AST</span>
                </div>
                <textarea
                    placeholder="Ask about any change. EVUA can explain AST transforms and AI reasoning for this file."
                    className="w-full h-32 bg-black/40 text-sm p-2 rounded-md border border-zinc-700 text-white focus:outline-none"
                ></textarea>
                <Button className="mt-3 w-full bg-gray-800 hover:bg-gray-700 text-white">Ask</Button>
            </CardContent>
        </Card>
    );
}