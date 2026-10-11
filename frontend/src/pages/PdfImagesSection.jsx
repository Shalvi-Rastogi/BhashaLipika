import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function PdfImagesSection({ documentId }) {
  const [images, setImages] = useState([]);

  useEffect(() => {
    if (!documentId) return;
    fetch(`${API}/review/pdf-images/${documentId}`)
      .then((r) => r.json())
      .then((d) => setImages(d.images || []))
      .catch(() => setImages([]));
  }, [documentId]);

  if (!images.length) return null;

  return (
    <section className="border-t border-[#d7dfdb] bg-[#f8faf9] p-4 sm:p-6">
      <h2 className="mb-4 text-base font-semibold text-[#26362f]">Images</h2>
      <div className="space-y-6">
        {images.map((img) => (
          <article
            key={`${img.page_number}-${img.image_index}`}
            className="overflow-hidden rounded border border-[#d7dfdb] bg-white"
          >
            <header className="border-b border-[#e5ebe7] px-4 py-3 text-sm font-semibold text-[#394840]">
              Page {img.page_number} - Image {img.image_index}
            </header>
            <div className="grid gap-4 p-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold text-[#87918c]">Original</p>
                {img.original_url && (
                  <img
                    src={`${API}${img.original_url}`}
                    alt="Original"
                    className="max-w-full rounded border border-[#e5ebe7]"
                  />
                )}
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold text-[#16734f]">Translated</p>
                {img.translated_url && (
                  <img
                    src={`${API}${img.translated_url}`}
                    alt="Translated"
                    className="max-w-full rounded border border-[#e5ebe7]"
                  />
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default PdfImagesSection;