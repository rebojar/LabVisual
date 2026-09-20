/* O mesmo campo de arquivos de imagem/vídeo, configurado para uma pasta. */
(() => {
  const input = $('batchFiles');
  let controller = null, uploadId = null;
  const accepted = /\.(jpe?g|png|webp|bmp|tiff?)$/i;

  function copying(on) {
    folderUploading = on;
    for (const id of ['batchFiles', 'batchFolder', 'scanBatch']) $(id).disabled = on || batchBusy;
    $('cancelFolderCopy').classList.toggle('hidden', !on);
    $('cancelFolderCopy').disabled = !on;
    $('folderCopyProgress').classList.toggle('hidden', !on);
    $('startBatch').disabled = on || busy || batchBusy || !scanData;
  }

  function readFile(file, signal) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      const abort = () => reader.abort();
      const cleanup = () => signal.removeEventListener('abort', abort);
      reader.onload = () => { cleanup(); resolve(reader.result); };
      reader.onerror = () => { cleanup(); reject(new Error('Não consegui ler: ' + file.name)); };
      reader.onabort = () => { cleanup(); reject(new DOMException('Cópia cancelada.', 'AbortError')); };
      if (signal.aborted) { reject(new DOMException('Cópia cancelada.', 'AbortError')); return; }
      signal.addEventListener('abort', abort, { once: true });
      reader.readAsDataURL(file);
    });
  }

  input.addEventListener('cancel', () => {
    if (!folderUploading) $('scanStatus').textContent = 'Escolha cancelada. A pasta anterior foi mantida.';
  });
  $('cancelFolderCopy').onclick = () => { controller?.abort(); };
  input.addEventListener('change', async () => {
    if (batchBusy || folderUploading || !input.files.length) return;
    const all = Array.from(input.files), files = all.filter(file => accepted.test(file.name));
    if (!files.length || files.length > 5000) {
      $('scanStatus').textContent = 'Escolha uma pasta com 1 a 5.000 imagens compatíveis.';
      input.value = ''; return;
    }
    const large = files.find(file => file.size > 20000000);
    if (large) {
      $('scanStatus').textContent = large.name + ' excede 20 MB. Cada imagem do lote precisa respeitar esse limite.';
      input.value = ''; return;
    }
    const label = files[0].webkitRelativePath.split('/')[0];
    if (files.some(file => !file.webkitRelativePath.includes('/') || file.webkitRelativePath.split('/')[0] !== label)) {
      $('scanStatus').textContent = 'Este navegador não informou a pasta. Use a opção de caminho manual abaixo.';
      input.value = ''; return;
    }
    const manifest = files.map(file => ({ path: file.webkitRelativePath.split('/').slice(1).join('/'), bytes: file.size }));
    controller = new AbortController(); const signal = controller.signal;
    copying(true); $('folderCopyProgress').max = files.length; $('folderCopyProgress').value = 0;
    $('scanStatus').textContent = `Preparando cópia local de ${files.length} imagens. O encoder ainda não executou.`;
    try {
      // Não abortar a criação: guardar o identificador permite limpar a pasta temporária.
      const created = await post('/api/folder/start', { label, files: manifest }); uploadId = created.id;
      for (let index = 0; index < files.length; index++) {
        if (signal.aborted) throw new DOMException('Cópia cancelada.', 'AbortError');
        $('scanStatus').textContent = `Copiando para a bancada: ${index + 1}/${files.length} · ${manifest[index].path}`;
        const data = await readFile(files[index], signal);
        await post('/api/folder/file', { id: uploadId, path: manifest[index].path, file: data }, signal);
        $('folderCopyProgress').value = index + 1;
      }
      if (signal.aborted) throw new DOMException('Cópia cancelada.', 'AbortError');
      $('cancelFolderCopy').disabled = true;
      const result = await post('/api/folder/finish', { id: uploadId }); uploadId = null;
      $('batchFolder').value = result.folder; $('batchFolder').oninput();
      await $('scanBatch').onclick();
      $('folderChoice').textContent = `Pasta selecionada: ${result.label} · cópia local na bancada.`;
      if (scanData) {
        const ignored = all.length - files.length;
        $('scanStatus').textContent = `${scanData.count} imagens prontas para conferir. O encoder ainda não foi executado.` +
          (ignored === 1 ? ' 1 arquivo de outro formato ficou de fora.' : ignored ? ` ${ignored} arquivos de outros formatos ficaram de fora.` : '');
      }
    } catch (error) {
      if (uploadId) {
        try { await post('/api/folder/cancel', { id: uploadId }); }
        catch { /* O erro principal continua legível; nenhum conjunto concluído é apagado. */ }
      }
      $('scanStatus').textContent = error.name === 'AbortError'
        ? 'Cópia cancelada. A pasta anterior foi mantida.' : error.message;
      input.value = '';
    } finally {
      uploadId = null; controller = null; copying(false);
    }
  });
  window.addEventListener('pagehide', () => {
    if (!uploadId) return;
    fetch('/api/folder/cancel', { method: 'POST', keepalive: true,
      headers: { 'Content-Type': 'application/json', 'X-Lab-Key': key },
      body: JSON.stringify({ id: uploadId }) }).catch(() => {});
  });
})();
