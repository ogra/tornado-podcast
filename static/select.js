var selectedImage = null;
var selectedAudio = null;

function selectImage(image) {
  selectedImage = image;
}

function setImage() {
  document.getElementById("image").value = selectedImage;
}

function selectAudio(audio) {
  selectedAudio = audio;
}

function setAudio() {
  document.getElementById("audio").value = selectedAudio;
}
