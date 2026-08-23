(() => {
  document.querySelectorAll('.csn-topnav').forEach((nav) => {
    const items = [...nav.querySelectorAll('.csn-item')];
    const closeAll = (except) => {
      items.forEach((item) => {
        if (item === except) return;
        item.removeAttribute('data-open');
        item.querySelector(':scope > button')?.setAttribute('aria-expanded', 'false');
      });
      if (!except) nav.removeAttribute('data-menu-open');
    };
    items.forEach((item) => {
      const button = item.querySelector(':scope > button');
      if (!button) return;
      button.addEventListener('click', (event) => {
        event.stopImmediatePropagation();
        const opening = item.getAttribute('data-open') !== 'true';
        closeAll(item);
        if (opening) {
          item.setAttribute('data-open', 'true');
          nav.setAttribute('data-menu-open', 'true');
        } else {
          item.removeAttribute('data-open');
          nav.removeAttribute('data-menu-open');
        }
        button.setAttribute('aria-expanded', String(opening));
      }, { capture: true });
    });
    document.addEventListener('click', () => closeAll());
    nav.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeAll();
    });
  });
})();
