import { useState, useMemo } from 'react';
import { Plus, Minus, Move, ChevronDown, ChevronUp, Sparkles, Terminal } from 'lucide-react';
import { Card, Badge } from '@/shared/ui';

export interface SkillPoint {
  name: string;
  points: number;
  category?: string;
}

const DEFAULT_RADAR_SKILLS: SkillPoint[] = [
  { name: 'Network & System', points: 45, category: 'SysAdmin' },
  { name: 'Project Admin', points: 65, category: 'Management' },
  { name: 'SQL', points: 58, category: 'Database' },
  { name: 'C++', points: 78, category: 'Systems' },
  { name: 'Linux', points: 88, category: 'SysAdmin' },
  { name: 'C', points: 94, category: 'Systems' },
  { name: 'DevOps', points: 62, category: 'SysAdmin' },
  { name: 'OOP', points: 75, category: 'Architecture' },
  { name: 'Shell/Bash', points: 82, category: 'Systems' },
  { name: 'DB & Data', points: 55, category: 'Database' },
  { name: 'Web', points: 80, category: 'Web' },
  { name: 'HTML/CSS', points: 88, category: 'Web' },
  { name: 'Frontend', points: 92, category: 'Web' },
  { name: 'JavaScript', points: 90, category: 'Web' },
  { name: 'TypeScript', points: 85, category: 'Web' },
  { name: 'UI & Design', points: 42, category: 'Design' },
  { name: 'Structured Prog', points: 96, category: 'Core' },
  { name: 'Data Structures', points: 92, category: 'Core' },
  { name: 'Architecture', points: 78, category: 'Architecture' },
  { name: 'Info Security', points: 65, category: 'Security' },
  { name: 'Project Mgmt', points: 50, category: 'Management' },
  { name: 'Graphics', points: 35, category: 'Media' },
  { name: 'Algorithms', points: 88, category: 'Core' },
  { name: 'Backend', points: 82, category: 'Web' },
  { name: 'Analytical', points: 85, category: 'Core' },
  { name: 'Mobile', points: 38, category: 'Mobile' },
  { name: 'Swift', points: 28, category: 'Mobile' },
  { name: 'Java', points: 48, category: 'Systems' },
  { name: 'Kotlin', points: 32, category: 'Mobile' },
  { name: 'Go', points: 60, category: 'Backend' },
  { name: 'Research', points: 70, category: 'Core' },
  { name: 'Python', points: 75, category: 'Scripting' },
  { name: 'C#', points: 45, category: 'Systems' },
  { name: 'Cryptography', points: 62, category: 'Security' },
  { name: 'Web Security', points: 68, category: 'Security' },
  { name: 'Code Review', points: 90, category: 'Quality' },
];

interface SkillsRadarWheelProps {
  userSkills?: SkillPoint[];
}

export function SkillsRadarWheel({ userSkills }: SkillsRadarWheelProps) {
  const [zoom, setZoom] = useState(1);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [hoveredSkill, setHoveredSkill] = useState<SkillPoint | null>(null);

  // Combine real user skills with default radar web layout
  const skillsData = useMemo(() => {
    if (!userSkills || userSkills.length === 0) return DEFAULT_RADAR_SKILLS;
    
    const userSkillMap = new Map(userSkills.map((s) => [s.name.toLowerCase(), s.points]));
    
    return DEFAULT_RADAR_SKILLS.map((item) => {
      const foundValue = userSkillMap.get(item.name.toLowerCase());
      return {
        ...item,
        points: foundValue !== undefined ? foundValue : item.points,
      };
    });
  }, [userSkills]);

  // Geometry dimensions
  const size = 640;
  const center = size / 2;
  const radius = 210;
  const numRings = 6;
  const totalSkills = skillsData.length;
  const maxSkillValue = 100;

  // Compute polar coordinates for all skill nodes
  const skillNodes = useMemo(() => {
    return skillsData.map((skill, index) => {
      const angle = (index / totalSkills) * 2 * Math.PI - Math.PI / 2;
      const normalizedValue = Math.min(Math.max(skill.points / maxSkillValue, 0.08), 1);
      const pointRadius = radius * normalizedValue;

      const x = center + pointRadius * Math.cos(angle);
      const y = center + pointRadius * Math.sin(angle);

      const labelRadius = radius + 22;
      const labelX = center + labelRadius * Math.cos(angle);
      const labelY = center + labelRadius * Math.sin(angle);

      // Text alignment anchor logic
      let textAnchor: 'start' | 'middle' | 'end' = 'middle';
      const cosA = Math.cos(angle);
      if (cosA > 0.25) textAnchor = 'start';
      else if (cosA < -0.25) textAnchor = 'end';

      return {
        ...skill,
        angle,
        x,
        y,
        labelX,
        labelY,
        textAnchor,
      };
    });
  }, [skillsData, center, radius, totalSkills]);

  // Generate SVG polygon points string for data area
  const polygonPointsStr = useMemo(() => {
    return skillNodes.map((n) => `${n.x.toFixed(1)},${n.y.toFixed(1)}`).join(' ');
  }, [skillNodes]);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 2.2));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.65));
  const handleResetZoom = () => setZoom(1);

  return (
    <Card className="flex flex-col border-2 border-black rounded-3xl bg-[#232D3B] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
      {/* Header bar */}
      <header className="flex items-center justify-between px-5 py-4 border-b-2 border-black/40 bg-[#1E2734]">
        <div className="flex items-center gap-2.5">
          <Terminal className="h-5 w-5 text-[#38C9E6]" />
          <h2 className="text-sm sm:text-base font-black text-white font-montserrat uppercase tracking-wider">
            Skills Radar & Competency Wheel
          </h2>
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg border-2 border-black bg-[#2A3442] text-white hover:bg-[#34495E] transition-all shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] active:translate-y-0.5"
          title={isCollapsed ? "Expand" : "Collapse"}
        >
          {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </button>
      </header>

      {!isCollapsed && (
        <div className="relative w-full flex flex-col items-center justify-center p-2 sm:p-6 overflow-hidden">
          {/* Zoom / Navigation Controls */}
          <div className="absolute right-3 bottom-3 sm:bottom-auto sm:right-auto sm:left-4 sm:top-1/2 sm:-translate-y-1/2 z-20 flex flex-row sm:flex-col gap-1.5 sm:gap-2 bg-[#1E2734]/90 backdrop-blur-xs p-1.5 rounded-2xl border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
            <button
              onClick={handleResetZoom}
              className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-[#2A3442] hover:bg-[#34495E] border-2 border-black flex items-center justify-center text-[#38C9E6] hover:text-white transition-colors"
              title="Reset Zoom"
            >
              <Move className="h-4 w-4" />
            </button>
            <div className="w-0.5 sm:w-full h-full sm:h-0.5 bg-black/40 my-0 sm:my-0.5" />
            <button
              onClick={handleZoomIn}
              className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-[#2A3442] hover:bg-[#34495E] border-2 border-black flex items-center justify-center text-white font-bold transition-colors"
              title="Zoom In"
            >
              <Plus className="h-4 w-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="h-8 w-8 sm:h-9 sm:w-9 rounded-xl bg-[#2A3442] hover:bg-[#34495E] border-2 border-black flex items-center justify-center text-white font-bold transition-colors"
              title="Zoom Out"
            >
              <Minus className="h-4 w-4" />
            </button>
          </div>

          {/* Hover Skill Tooltip Indicator */}
          {hoveredSkill && (
            <div className="absolute top-2 left-2 right-2 sm:left-auto sm:right-4 sm:top-4 z-20 bg-[#1E2734] border-2 border-black p-3 rounded-2xl shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] flex items-center gap-3 animate-fade-in">
              <div className="h-8 w-8 rounded-xl bg-[#38C9E6] text-black font-black text-xs flex items-center justify-center border border-black">
                {hoveredSkill.points}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-black text-white font-montserrat uppercase truncate">
                  {hoveredSkill.name}
                </span>
                <span className="text-[10px] text-[#43E8A0] font-bold">
                  {hoveredSkill.category || 'Skill Competency'}
                </span>
              </div>
            </div>
          )}

          {/* SVG Radar Wheel Graphic */}
          <div className="w-full max-w-[700px] aspect-square flex items-center justify-center overflow-hidden">
            <svg
              viewBox={`-35 -30 ${size + 70} ${size + 60}`}
              className="w-full h-full transition-transform duration-300 ease-out select-none"
              style={{ transform: `scale(${zoom})` }}
            >
              <defs>
                {/* Mint Glow filter */}
                <filter id="radarGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <linearGradient id="polyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#43E8A0" stopOpacity="0.45" />
                  <stop offset="100%" stopColor="#38C9E6" stopOpacity="0.25" />
                </linearGradient>
              </defs>

              {/* Concentric Polar Grid Rings */}
              {Array.from({ length: numRings }).map((_, i) => {
                const r = (radius / numRings) * (i + 1);
                return (
                  <circle
                    key={i}
                    cx={center}
                    cy={center}
                    r={r}
                    fill="none"
                    stroke="#4A5568"
                    strokeWidth="1"
                    strokeDasharray={i === numRings - 1 ? 'none' : '2,2'}
                    opacity={0.5 + (i / numRings) * 0.4}
                  />
                );
              })}

              {/* Radial Spoke Lines */}
              {skillNodes.map((node, idx) => (
                <line
                  key={idx}
                  x1={center}
                  y1={center}
                  x2={center + radius * Math.cos(node.angle)}
                  y2={center + radius * Math.sin(node.angle)}
                  stroke="#4A5568"
                  strokeWidth="0.8"
                  opacity="0.6"
                />
              ))}

              {/* Data Polygon Fill */}
              <polygon
                points={polygonPointsStr}
                fill="url(#polyGrad)"
                stroke="#43E8A0"
                strokeWidth="2.5"
                filter="url(#radarGlow)"
              />

              {/* Skill Nodes & Labels */}
              {skillNodes.map((node, idx) => {
                const isHovered = hoveredSkill?.name === node.name;

                return (
                  <g
                    key={idx}
                    className="cursor-pointer transition-all duration-150"
                    onMouseEnter={() => setHoveredSkill(node)}
                    onMouseLeave={() => setHoveredSkill(null)}
                  >
                    {/* Node Dot */}
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={isHovered ? 6 : 3.5}
                      fill={isHovered ? '#FFFFFF' : '#43E8A0'}
                      stroke="#1E2734"
                      strokeWidth="1.5"
                      className="transition-all duration-200"
                    />

                    {/* Skill Label Text */}
                    <text
                      x={node.labelX}
                      y={node.labelY}
                      textAnchor={node.textAnchor}
                      dominantBaseline="central"
                      fill={isHovered ? '#43E8A0' : '#E2E8F0'}
                      fontSize={isHovered ? '11' : '9.5'}
                      fontWeight={isHovered ? '900' : '600'}
                      fontFamily="IBM Plex Mono, monospace"
                      className="transition-colors duration-150"
                    >
                      {node.name}
                    </text>
                  </g>
                );
              })}

              {/* Center Pivot Point */}
              <circle cx={center} cy={center} r="4" fill="#38C9E6" stroke="#1E2734" strokeWidth="2" />
            </svg>
          </div>

          {/* Footer Legend */}
          <footer className="w-full pt-3 border-t border-black/20 flex flex-wrap items-center justify-between text-[10px] text-[#B0BEC5] font-bold px-2 gap-2">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-[#43E8A0] border border-black" />
              <span>Competency Coverage</span>
            </div>
            <div className="flex items-center gap-1.5 text-white">
              <Sparkles className="h-3.5 w-3.5 text-[#38C9E6]" />
              <span>Hover skill nodes to inspect rating</span>
            </div>
          </footer>
        </div>
      )}
    </Card>
  );
}

export default SkillsRadarWheel;
