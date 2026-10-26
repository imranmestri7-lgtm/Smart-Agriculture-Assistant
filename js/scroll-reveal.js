// scroll-reveal.js – lightweight IntersectionObserver implementation
// Elements with the attribute `data-reveal` will receive the class `visible`
// when they intersect the viewport. The animation runs only once.

(function(){
  const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
  };

  const revealCallback = (entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        obs.unobserve(entry.target); // stop observing after reveal
      }
    });
  };

  const observer = new IntersectionObserver(revealCallback, observerOptions);

  // Query all elements with data-reveal attribute
  document.addEventListener('DOMContentLoaded', () => {
    const revealElements = document.querySelectorAll('[data-reveal]');
    revealElements.forEach(el => observer.observe(el));
  });
})();
