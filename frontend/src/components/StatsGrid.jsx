import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

export default function StatsGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
      {/* Total Files Scanned */}
      <Card className="bg-[#0b0b0b] text-white border border-zinc-800 rounded-xl shadow-inner">
        <CardContent className="p-6">
          <p className="text-zinc-400 text-base mb-3">Total Files Scanned</p>
          <h2 className="text-4xl font-bold tracking-wide mt-3">384</h2>
        </CardContent>
      </Card>

      {/* Deprecated Syntax Fixed */}
      <Card className="bg-[#0b0b0b] text-white border border-zinc-800 rounded-xl shadow-inner">
        <CardContent className="p-6">
          <p className="text-zinc-400 text-base mb-3">Deprecated Syntax Fixed</p>
          <h2 className="text-4xl font-bold tracking-wide mt-3">1,276</h2>
        </CardContent>
      </Card>

      {/* Overall Upgrade Progress */}
      <Card className="bg-[#0b0b0b] text-white border border-zinc-800 rounded-xl shadow-inner">
        <CardContent className="p-6">
          <p className="text-zinc-400 text-base mb-3">Overall Upgrade Progress</p>
          <h2 className="text-4xl font-bold tracking-wide mt-3">44%</h2>
          <Progress
            value={44}
            className="mt-4 bg-zinc-800"
          />
        </CardContent>
      </Card>
    </div>
  );
}
