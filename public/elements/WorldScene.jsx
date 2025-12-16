import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Heart, Shield } from "lucide-react";

export default function WorldScene() {
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
      druid: "🌿",
    };
    return icons[className?.toLowerCase()] || "⚔️";
  };

  return (
    <div className="relative w-full">
      {/* World Map Background */}
      <div className="relative w-full rounded-xl overflow-hidden shadow-2xl">
        <img
          src={props.mapImagePath || "/placeholder.svg"}
          alt="World Map"
          className="w-full h-auto object-cover"
        />

        {/* Gradient overlay for better text/card visibility */}
        <div className="absolute inset-0 bg-gradient-to-br from-black/40 via-transparent to-black/30 pointer-events-none" />

        {/* Scene Title Overlay */}
        <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/70 to-transparent p-6">
          <h2 className="text-3xl font-serif font-bold text-amber-100 drop-shadow-lg">
            {props.sceneTitle || "The Adventure Begins"}
          </h2>
          {props.sceneTagline && (
            <p className="text-amber-200 italic text-lg mt-2 drop-shadow-md">
              {props.sceneTagline}
            </p>
          )}
        </div>

        {/* Character Cards - Absolutely Positioned Top Left */}
        {props.characters && props.characters.length > 0 && (
          <div className="absolute bottom-2 left-6 flex w-full justify-between px-2 gap-3 max-w-[220px] card-container">
            {props.characters.map((character, index) => {
              const hpPercentage = (character.hp / character.maxHp) * 100;

              return (
                <Card
                  key={index}
                  className="bg-gradient-to-br from-stone-900/95 via-amber-950/95 to-stone-900/95 border-2 border-amber-700 shadow-2xl backdrop-blur-sm"
                >
                  <CardContent className="p-3">
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-amber-600 shadow-lg flex-shrink-0">
                        <img
                          src={character.imagePath || "/placeholder.svg"}
                          alt={character.name}
                          className="h-full object-cover"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-amber-100 font-bold text-sm truncate">
                          {character.name}
                        </h3>
                        <div className="flex gap-1 flex-wrap">
                          <Badge className="bg-purple-700 text-purple-100 text-xs px-1 py-0">
                            {character.race}
                          </Badge>
                          <Badge className="bg-blue-700 text-blue-100 text-xs px-1 py-0">
                            {character.className}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Stats Row */}
                    <div className="flex items-center gap-2 mb-2">
                      <div className="flex items-center gap-1 bg-blue-900/50 rounded px-2 py-1 border border-blue-700">
                        <Shield className="h-3 w-3 text-blue-300" />
                        <span className="text-blue-100 font-bold text-xs">
                          {character.ac}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 bg-amber-900/50 rounded px-2 py-1 border border-amber-700">
                        <span className="text-amber-200 font-bold text-xs">
                          Lvl {character.level}
                        </span>
                      </div>
                    </div>

                    {/* HP Bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <Heart
                            className={`h-3 w-3 ${
                              hpPercentage > 30
                                ? "text-red-400"
                                : "text-red-600 animate-pulse"
                            }`}
                          />
                          <span className="text-amber-200 text-xs font-semibold">
                            HP
                          </span>
                        </div>
                        <span className="text-amber-100 text-xs font-bold">
                          {character.hp}/{character.maxHp}
                        </span>
                      </div>
                      <Progress
                        value={hpPercentage}
                        className="h-2 bg-stone-950"
                      >
                        <div
                          className={`h-full transition-all rounded-full ${
                            hpPercentage > 60
                              ? "bg-green-600"
                              : hpPercentage > 30
                              ? "bg-yellow-600"
                              : "bg-red-600"
                          }`}
                          style={{ width: `${hpPercentage}%` }}
                        />
                      </Progress>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
