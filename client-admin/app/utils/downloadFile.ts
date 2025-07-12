type DownloadFileData = {
  data: string; // Base64 encoded string
  filename: string;
  contentType: string;
};

export function downloadFile({ data, filename, contentType }: DownloadFileData) {
  // Base64文字列をUint8Arrayに変換
  const binaryString = atob(data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const blob = new Blob([bytes], { type: contentType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}
