// Auto-dismiss Bootstrap toasts after 4 seconds
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach((toast) => {
        setTimeout(() => {
            toast.classList.remove("show");
        }, 4000);
    });
});

// CSRF helper for future AJAX calls
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
}

window.connectly = {
    csrfToken: () => getCookie("csrftoken"),
};