export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-2">
      {[0, 1, 2].map(i => (
        <div
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
          style={{ animationDelay: `${i * 0.15}s`, animationDuration: "0.8s" }}
        />
      ))}
    </div>
  );
}
