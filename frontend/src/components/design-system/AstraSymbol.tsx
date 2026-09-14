import { Info, BookOpen, Paperclip, CheckCircle2, AlertTriangle, Trophy, Clock, RotateCcw, Search, Box, FlaskConical, Users, GraduationCap, Ban, FileText, Lightbulb, Star, Gamepad2 } from "lucide-react";

/** Consistent vector icons for legacy UI labels; decorative glyphs never become text. */
export function AstraSymbol({ value }: { value: string }) {
  const icons: Record<string, typeof Info> = {
    "ℹ": Info, "🎉": CheckCircle2, "✅": CheckCircle2, "❌": Ban, "⚠": AlertTriangle,
    "📚": BookOpen, "📘": BookOpen, "📝": FileText, "📎": Paperclip,
    "⏱": Clock, "⏳": Clock, "🔄": RotateCcw, "🔍": Search, "👀": Info,
    "🧊": Box, "🔬": FlaskConical, "👥": Users, "🎓": GraduationCap,
    "🏆": Trophy, "👑": Trophy, "🚫": Ban, "💡": Lightbulb, "⭐": Star,
    "🎮": Gamepad2, "📊": Info, "📐": Info,
  };
  const Icon = icons[value.replace(/\uFE0F/g, "")] || Info;
  return <Icon size={16} className="astra-inline-icon" aria-hidden="true" />;
}
