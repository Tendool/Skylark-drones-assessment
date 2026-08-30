// Minimal, dependency-free renderer for the markdown-ish subset the agent's
// text tends to use (paragraphs, "- " bullets, "1. " numbered lists, **bold**,
// "### " headings). Builds React elements directly rather than raw HTML, so
// there's no injection risk from rendering model output.

function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 3) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>;
  });
}

export default function MarkdownLite({ text }) {
  const lines = text.split("\n");
  const blocks = [];
  let listBuffer = [];
  let listType = null;

  const flushList = (key) => {
    if (listBuffer.length === 0) return;
    const Tag = listType === "ol" ? "ol" : "ul";
    blocks.push(
      <Tag key={`list-${key}`}>
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item, `li-${key}-${i}`)}</li>
        ))}
      </Tag>
    );
    listBuffer = [];
    listType = null;
  };

  lines.forEach((line, idx) => {
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const bullet = line.match(/^[-*]\s+(.*)/);
    const numbered = line.match(/^\d+\.\s+(.*)/);

    if (heading) {
      flushList(idx);
      const Tag = `h${Math.min(heading[1].length + 3, 6)}`;
      blocks.push(<Tag key={idx}>{renderInline(heading[2], `h-${idx}`)}</Tag>);
    } else if (bullet) {
      if (listType && listType !== "ul") flushList(idx);
      listType = "ul";
      listBuffer.push(bullet[1]);
    } else if (numbered) {
      if (listType && listType !== "ol") flushList(idx);
      listType = "ol";
      listBuffer.push(numbered[1]);
    } else if (line.trim() === "") {
      flushList(idx);
    } else {
      flushList(idx);
      blocks.push(<p key={idx}>{renderInline(line, `p-${idx}`)}</p>);
    }
  });
  flushList("end");

  return <>{blocks}</>;
}
