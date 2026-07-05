export default function SourceCard({ source }) {
  return (
    <span className="source-card" title={source}>
      📄 {source}
    </span>
  );
}
