function getPgs(pdoc_id) {
  const selector = `#pdoc-${pdoc_id} .page-image`;
  return document.querySelectorAll(selector);
}

function getArray(pdoc_id) {
  const pgs = getPgs(pdoc_id);
  const array = [];
  pgs.forEach((pg, pg_num) => {
    if (!array.length)
      array.push([]);
    array[array.length-1].push(pg_num);
    if (pg.classList.contains('end') && pg_num !== pgs.length - 1)
      array.push([]);
  });
  // turn the lists into start, end tuples
  return array.filter(x=>x&&x.length).map(x=>{;
    return [x[0], x[x.length-1]];
  });
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
          }
      }
  }
  return cookieValue;
}

async function saveSegments(pdoc_id) {
  console.log(pdoc_id);
  const array = getArray(pdoc_id);
  console.log("array:", array);

  const csrftoken = getCookie('csrftoken');
  const formData = new FormData();
  formData.append('incident_pgs', JSON.stringify(array));
  const response = await fetch(`/api/save-segments/${pdoc_id}`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
    },
    body: formData,
  });
}

function applySegments(pdoc_id, incident_pgs) {
  console.log("applying segments", pdoc_id, incident_pgs);
  const pgs = getPgs(pdoc_id);
  pgs.forEach((pg) => {
    pg.classList.remove("end");
  });
  (incident_pgs || []).forEach(([start, end]) => {
    for (let i = start; i < end; i++) {
      pgs[end].classList.remove('end');
    }
    pgs[end].classList.add('end');
  });
}

function zoomPage(img_data, event) {
  const element = document.getElementById("zoomed-page");
  element.style.backgroundImage = `url('${img_data.url}')`;
  element.style.backgroundSize = "180%";
  element.style.display = "inline-block";
  const img = event.target;
  var posX = event.offsetX ? (event.offsetX) : event.pageX - img.offsetLeft;
  var posY = event.offsetY ? (event.offsetY) : event.pageY - img.offsetTop;
  element.style.backgroundPosition = ((posX / img.offsetWidth)*100) + "% " + ((posY / img.offsetHeight)*100) + "%";
}

function zoomOut(img_data, event) {
  const element = document.getElementById("zoomed-page");
  element.style.backgroundImage = `url('${img_data.url}')`;
  element.style.backgroundPosition = "0 0";
  element.style.backgroundSize = "contain";
}

// window.saveSegments = saveSegments;
// document.saveSegments = saveSegments;
