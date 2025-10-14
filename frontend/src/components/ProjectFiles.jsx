import { Card, CardContent } from '@/components/ui/card';
import { projectFiles } from '@/data/files';


export default function ProjectFiles({ selectedFile, setSelectedFile }) {
    return (
        <Card className="col-span-1 bg-zinc-900 border-zinc-800">
            <CardContent className="p-4">
                <h3 className="text-lg font-semibold mb-4">Project Files</h3>
                <ul className="space-y-2">
                    {projectFiles.map((file) => (
                        <li
                            key={file.name}
                            onClick={() => setSelectedFile(file.name)}
                            className={`cursor-pointer p-2 rounded-lg flex items-center gap-2 transition-colors duration-200 ${selectedFile === file.name ? 'bg-zinc-800 text-white' : 'hover:bg-zinc-800 text-zinc-400'
                                }`}
                        >
                            <span
                                className={`w-2 h-2 rounded-full ${file.status === 'upgraded'
                                        ? 'bg-white'
                                        : file.status === 'pending'
                                            ? 'bg-gray-500'
                                            : 'bg-red-500'
                                    }`}
                            ></span>
                            {file.name}
                        </li>
                    ))}
                </ul>
            </CardContent>
        </Card>
    );
}