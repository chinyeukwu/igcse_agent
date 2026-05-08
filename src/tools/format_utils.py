
def format_table(data: str) -> dict:
    rows = data.strip().split("\n")
    html = "<table border='1' cellpadding='5'><tr>"
    headers = rows[0].split(",")
    html += ''.join(f"<th>{h.strip()}</th>" for h in headers) + "</tr>"
    for row in rows[1:]:
        html += "<tr>" + ''.join(f"<td>{cell.strip()}</td>" for cell in row.split(",")) + "</tr>"
    html += "</table>"
    return {"html": html, "csv": data}