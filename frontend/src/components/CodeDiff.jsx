import { Card, CardContent } from '@/components/ui/card';


export default function CodeDiff({ codeDiff }) {
    return (
        <div className="col-span-2 grid grid-cols-2 gap-4">
            <Card className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-4">
                    <h3 className="text-sm font-semibold mb-2">Python 2</h3>
                    <pre className="bg-black/40 p-3 rounded-md text-red-400 text-sm overflow-auto h-64 whitespace-pre-wrap">{codeDiff.py2}</pre>
                </CardContent>
            </Card>


            <Card className="bg-zinc-900 border-zinc-800">
                <CardContent className="p-4">
                    <h3 className="text-sm font-semibold mb-2">Python 3</h3>
                    <pre className="bg-black/40 p-3 rounded-md text-green-400 text-sm overflow-auto h-64 whitespace-pre-wrap">{codeDiff.py3}</pre>
                </CardContent>
            </Card>
        </div>
    );
}