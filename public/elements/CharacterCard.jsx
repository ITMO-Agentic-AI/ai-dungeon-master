import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Heart, Shield } from "lucide-react"

export default function CharacterCard() {
  const hpPercentage = (props.hp / props.maxHp) * 100;
  
  const getClassIcon = (className) => {
    const icons = {
      warrior: "⚔️",
      fighter: "⚔️",
      wizard: "🔮",
      mage: "🔮",
      rogue: "🗡️",
      thief: "🗡️",
      cleric: "✝️",
      priest: "✝️",
      paladin: "🛡️",
      ranger: "🏹",
      bard: "🎵",
      druid: "🌿"
    };
    return icons[className?.toLowerCase()] || "⚔️";
  };

  return (
    <div className="max-w-[250px] relative">
      {/* Card Border with Ornate Styling */}
      <div className="relative bg-gradient-to-br from-amber-900 via-yellow-900 to-amber-950 rounded-3xl p-4 shadow-2xl border-4 border-amber-700">
        {/* Inner Card */}
        <div className="bg-gradient-to-br from-stone-800 via-neutral-900 to-stone-900 rounded-2xl overflow-hidden">
          {/* Header Section */}
          <div className="relative bg-gradient-to-r from-amber-800 via-yellow-800 to-amber-900 px-4 py-3 border-b-4 border-amber-950">
            <div className="flex items-center justify-between">
              {/* Class Icon */}
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-900 to-purple-950 border-2 border-amber-600 flex items-center justify-center text-2xl">
                {getClassIcon(props.className)}
              </div>

              {/* Title */}
              <h2 className="text-amber-100 font-serif text-xl font-bold tracking-wide text-center flex-1 uppercase">
                {props.name}
              </h2>

              {/* Level Badge */}
              <div className="flex items-center gap-1">
                <span className="text-amber-200 text-xs font-semibold">LVL</span>
                <Badge className="bg-gradient-to-br from-amber-700 to-amber-900 text-amber-100 font-bold text-base border-2 border-amber-600 px-2">
                  {props.level}
                </Badge>
              </div>
            </div>
          </div>

          {/* Image Section */}
          <div className="relative aspect-square bg-gradient-to-br from-purple-950 via-stone-900 to-amber-950 border-b-4 border-amber-950">
            <img src={props.imagePath || "/placeholder.svg"} alt={props.name} className="w-full h-full object-cover" />

            {/* Stats Badges */}
            <div className="absolute top-4 right-4 flex flex-col gap-2">
              {/* AC Badge */}
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-800 to-blue-950 border-4 border-amber-600 flex flex-col items-center justify-center shadow-lg">
                <Shield className="h-4 w-4 text-blue-300" />
                <span className="text-lg text-blue-100 font-bold">{props.ac}</span>
              </div>

              {/* HP Badge */}
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-red-800 to-red-950 border-4 border-amber-700 flex flex-col items-center justify-center shadow-lg">
                <Heart className="h-4 w-4 text-red-300" />
                <span className="text-sm text-red-100 font-bold">{props.hp}</span>
              </div>
            </div>

            {/* Race/Class Badges */}
            <div className="absolute bottom-4 left-4 flex gap-2">
              <Badge className="bg-gradient-to-br from-purple-700 to-purple-900 text-purple-100 font-semibold border-2 border-purple-600">
                {props.race}
              </Badge>
              <Badge className="bg-gradient-to-br from-blue-700 to-blue-900 text-blue-100 font-semibold border-2 border-blue-600">
                {props.className}
              </Badge>
            </div>

            {/* Decorative Side Pattern */}
            <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-amber-900/80 to-transparent border-r-2 border-amber-800/50">
              <div className="flex flex-col items-center justify-center h-full gap-3 text-amber-700 text-xs">
                {"⚔️🛡️🗡️⚔️🛡️".split("").map((icon, i) => (
                  <span key={i} className="opacity-60">
                    {icon}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* HP Bar Section */}
          <div className="bg-gradient-to-br from-stone-900 to-amber-950 px-4 py-3 border-b-4 border-amber-950">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Heart className={`h-5 w-5 ${hpPercentage > 30 ? 'text-red-500' : 'text-red-700 animate-pulse'}`} />
                <span className="font-semibold text-amber-200">Health Points</span>
              </div>
              <span className="text-lg font-bold text-amber-100">
                {props.hp} / {props.maxHp}
              </span>
            </div>
            <Progress value={hpPercentage} className="h-3 bg-stone-950">
              <div 
                className={`h-full transition-all rounded-full ${
                  hpPercentage > 60 ? 'bg-green-600' : hpPercentage > 30 ? 'bg-yellow-600' : 'bg-red-600'
                }`} 
                style={{ width: `${hpPercentage}%` }} 
              />
            </Progress>
          </div>

          {/* Character Details Section */}
          <div className="bg-gradient-to-br from-amber-100 via-yellow-50 to-amber-50 p-4 space-y-3">
            {props.background && (
              <div className="bg-gradient-to-br from-stone-100 to-amber-50 rounded-lg p-3 border-2 border-amber-800 shadow-sm">
                <div className="flex items-start gap-2">
                  <span className="text-2xl mt-0.5">📜</span>
                  <div className="flex-1">
                    <h3 className="text-stone-900 font-bold text-base mb-1">Background</h3>
                    <p className="text-stone-700 text-sm leading-relaxed">{props.background}</p>
                  </div>
                </div>
              </div>
            )}

            {props.motivation && (
              <div className="bg-gradient-to-br from-stone-100 to-amber-50 rounded-lg p-3 border-2 border-amber-800 shadow-sm">
                <div className="flex items-start gap-2">
                  <span className="text-2xl mt-0.5">💫</span>
                  <div className="flex-1">
                    <h3 className="text-stone-900 font-bold text-base mb-1">Motivation</h3>
                    <p className="text-stone-700 text-sm leading-relaxed">{props.motivation}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
