import { Button } from '@/components/ui/button';


export default function FooterActions() {
    return (
        <div className="flex justify-end mt-6 gap-3">
            <Button className="bg-gray-800 hover:bg-gray-700 text-white">Next File</Button>
            <Button className="bg-gray-800 hover:bg-gray-700 text-white">Download Upgraded Code</Button>
        </div>
    );
}