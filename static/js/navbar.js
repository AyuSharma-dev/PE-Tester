var modal = document.getElementById("myModal");
var span = document.getElementsByClassName("close")[0];
var btn = document.getElementById("myBtn");
var btn2 = document.getElementById("ib");
document.body.style.zoom = 1.0;

btn2.onclick = function () {
    if (btn2.innerHTML === "Okay if you really want to know click here") {
        btn2.innerHTML = 'Click here to view steps';
        btn2.style.fontSize = '60px';
        btn2.style.width = '50%';
        btn2.style.marginTop = '16%';
        document.getElementById("tip2").style.display = 'block';
        document.getElementById("tip1").style.display = 'none'
    } else {
        btn2.style.display = 'none';
        document.getElementById("tip2").style.display = 'none';
        document.getElementById("tip3").style.display = 'block';
    }

}

btn.onclick = function () {
    modal.style.display = "block";
}


span.onclick = function () {
    modal.style.display = "none";
}

window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}