document.addEventListener('DOMContentLoaded', () => {
    // Get the navbar-burger element and the navbar-menu
    const navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
    const navbarMenu = document.getElementById('navbarMenu');

    // Check if there are any navbar burgers
    if (navbarBurgers.length > 0) {
        // Add click event to toggle the navbar menu
        navbarBurgers.forEach(el => {
            el.addEventListener('click', () => {
                // Toggle the class on both the navbar burger and the navbar menu
                el.classList.toggle('is-active');
                navbarMenu.classList.toggle('is-active');
            });
        });
    }
});