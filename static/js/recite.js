// scripts.js

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById('home-button').addEventListener('click', function () {
        window.location.href = '/';
    });

    document.getElementById('next-button').addEventListener('click', function () {
        window.location.href = '/next';
    });

    document.getElementById('mark-familiar').addEventListener('click', function () {
        window.location.href = '/familiar';
    });
});