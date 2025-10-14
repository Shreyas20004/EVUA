import { Button } from '@/components/ui/button';


export default function Header() {
    return (
        <div className="flex justify-between items-center mb-8">
            <h1 className="text-2xl font-semibold">EVUA</h1>
            <Button className="bg-white hover:bg-gray-700 text-black">Select Project Folder</Button>
        </div>
    );
}