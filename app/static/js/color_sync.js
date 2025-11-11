'use strict';
(function () {
  function syncPicker(picker) {
    const textInput = picker.closest('.input-group')?.querySelector('input[type="text"]');
    if (!textInput) return;
    picker.addEventListener('input', () => { textInput.value = picker.value; });
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="color"]').forEach(syncPicker);
  });
})();
