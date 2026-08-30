// Minimal, dependency-free renderer for the markdown-ish subset the agent's
// text tends to use (paragraphs, "- " bullets, "1. " numbered lists,
// **bold**, "### " headings, "---" rules, and GFM-style "| a | b |" tables).
// Builds React elements directly rather than raw HTML, so there's no
// injection risk from rendering model output.

function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 3) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>;
  });
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

const TABLE_ROW_RE = /^\s*\|.*\|\s*$/;
const TABLE_SEPARATOR_RE = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

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

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const bullet = line.match(/^[-*]\s+(.*)/);
    const numbered = line.match(/^\d+\.\s+(.*)/);
    const isRule = /^\s*(---+|\*\*\*+|___+)\s*$/.test(line);
    const isTableStart =
      TABLE_ROW_RE.test(line) && i + 1 < lines.length && TABLE_SEPARATOR_RE.test(lines[i + 1]) && TABLE_ROW_RE.test(lines[i + 1]);

    if (isTableStart) {
      flushList(i);
      const headerCells = splitTableRow(line);
      const bodyRows = [];
      let j = i + 2;
      while (j < lines.length && TABLE_ROW_RE.test(lines[j])) {
        bodyRows.push(splitTableRow(lines[j]));
        j += 1;
      }
      blocks.push(
        <div className="table-scroll" key={`table-${i}`}>
          <table>
            <thead>
              <tr>
                {headerCells.map((cell, ci) => (
                  <th key={ci}>{renderInline(cell, `th-${i}-${ci}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci}>{renderInline(cell, `td-${i}-${ri}-${ci}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      i = j;
      continue;
    }

    if (isRule) {
      flushList(i);
      blocks.push(<hr key={i} />);
    } else if (heading) {
      flushList(i);
      const Tag = `h${Math.min(heading[1].length + 3, 6)}`;
      blocks.push(<Tag key={i}>{renderInline(heading[2], `h-${i}`)}</Tag>);
    } else if (bullet) {
      if (listType && listType !== "ul") flushList(i);
      listType = "ul";
      listBuffer.push(bullet[1]);
    } else if (numbered) {
      if (listType && listType !== "ol") flushList(i);
      listType = "ol";
      listBuffer.push(numbered[1]);
    } else if (line.trim() === "") {
      flushList(i);
    } else {
      flushList(i);
      blocks.push(<p key={i}>{renderInline(line, `p-${i}`)}</p>);
    }
    i += 1;
  }
  flushList("end");

  return <>{blocks}</>;
}
