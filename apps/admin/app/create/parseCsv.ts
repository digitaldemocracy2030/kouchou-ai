import * as chardet from "chardet";
import * as iconv from "iconv-lite";
import Papa from "papaparse";

export interface CsvData {
  id: string;
  comment: string;
  source?: string | null;
  url?: string | null;
  // Allow for dynamic attribute fields
  [key: string]: string | null | undefined;
}

export async function parseCsv(csvFile: File): Promise<CsvData[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = async () => {
      const arraybuffer = reader.result as ArrayBuffer;
      const buffer = new Uint8Array(arraybuffer);
      const nodeBuffer = Buffer.from(buffer);

      const detectedEncoding = chardet.detect(nodeBuffer) || "utf-8";

      const decodedText = iconv.decode(nodeBuffer, detectedEncoding);
      const utf8Text = iconv.encode(decodedText, "utf-8").toString();

      Papa.parse(utf8Text, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const data = results.data as CsvData[];
          const converted = data.map((row, index) => {
            // id または comment-id が存在する場合はその値を使用、存在しない場合は csv-${index + 1} を使用
            let finalId = `csv-${index + 1}`;

            if (row.id !== undefined && row.id !== null && row.id !== "") {
              finalId = String(row.id);
            } else if (row["comment-id"] !== undefined && row["comment-id"] !== null && row["comment-id"] !== "") {
              finalId = String(row["comment-id"]);
            }

            return {
              ...row,
              id: finalId,
            };
          });
          resolve(converted);
        },
        error: (error: Error) => {
          reject(error);
        },
      });
    };

    reader.onerror = (error) => {
      reject(error);
    };

    reader.readAsArrayBuffer(csvFile);
  });
}
