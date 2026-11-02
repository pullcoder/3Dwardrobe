// 검증된 이미지 바이트는 stdin으로만 받는다. 사용자 파일·OCR 캐시는 디스크에 쓰지 않는다.
import { createWorker } from 'tesseract.js';
import { fileURLToPath } from 'node:url';

let worker;
try {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  worker = await createWorker('kor+eng', 1, {
    langPath: fileURLToPath(new URL('./models', import.meta.url)),
    gzip: false,
    cacheMethod: 'none',
    logger: () => {},
    errorHandler: () => {},
  });
  await worker.setParameters({ tessedit_pageseg_mode: '6' });
  const { data } = await worker.recognize(Buffer.concat(chunks));
  process.stdout.write(JSON.stringify({ text: data.text, confidence: data.confidence }));
} catch {
  process.stderr.write('LOCAL_OCR_FAILED');
  process.exitCode = 1;
} finally {
  await worker?.terminate();
}
