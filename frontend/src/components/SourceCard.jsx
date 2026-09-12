export default function SourceCard({ source }) {
  if (!source) return null;
  const fileName = source.source_file || 'Unknown';
  const pageInfo = source.page !== null && source.page !== undefined ? `, p. ${source.page}` : '';
  const scoreInfo = source.score ? ` (Score: ${(source.score * 100).toFixed(0)}%)` : '';

  return (
    <span className="source-card" title={`${fileName}${pageInfo}${scoreInfo}`}>
      📄 {fileName}{pageInfo}
    </span>
  );
}

