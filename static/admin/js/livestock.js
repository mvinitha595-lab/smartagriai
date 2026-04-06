document.addEventListener("DOMContentLoaded", function () {
    const animalField = document.querySelector("#id_animal_type");
    const milkField = document.querySelector(".field-milk_per_day_litre");
    const eggField = document.querySelector(".field-eggs_per_day");

    function toggleYield() {
        if (!animalField) return;

        const animal = animalField.value;

        milkField.style.display = "none";
        eggField.style.display = "none";

        if (animal === "cow" || animal === "goat") {
            milkField.style.display = "block";
        }
        if (animal === "poultry") {
            eggField.style.display = "block";
        }
    }

    animalField.addEventListener("change", toggleYield);
    toggleYield();
});