"""Generate a small multi-page test PDF for tests."""
import pikepdf


def create_sample_pdf(path: str, num_pages: int = 3):
    pdf = pikepdf.Pdf.new()
    for i in range(num_pages):
        page_width = 612  # 8.5 inches in points
        page_height = 792  # 11 inches in points
        content = f"BT /F1 24 Tf 100 700 Td (Page {i + 1}) Tj ET".encode()
        page = pikepdf.Page(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Page,
                MediaBox=[0, 0, page_width, page_height],
                Contents=pdf.make_stream(content),
                Resources=pikepdf.Dictionary(
                    Font=pikepdf.Dictionary(
                        F1=pikepdf.Dictionary(
                            Type=pikepdf.Name.Font,
                            Subtype=pikepdf.Name.Type1,
                            BaseFont=pikepdf.Name.Helvetica,
                        )
                    )
                ),
            )
        )
        pdf.pages.append(page)
    pdf.save(path)


if __name__ == "__main__":
    create_sample_pdf("tests/fixtures/sample.pdf")
