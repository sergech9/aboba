const ws = new WebSocket("ws://" + location.host + "/ws")

ws.onmessage = function(event){

    const data = JSON.parse(event.data)

    if(data.type === "new_ticket"){

        addTicket(data.id, data.text)

        showNotification(data.text)
    }

    if(data.type === "close_ticket"){

        const el = document.getElementById("ticket-" + data.id)

        if(el){
            el.remove()
        }
    }
}


function addTicket(id, text){

    const div = document.createElement("div")

    div.id = "ticket-" + id

    div.innerHTML = `
        <pre>${text}</pre>
        <button onclick="closeTicket(${id})">Закрыть</button>
        <hr>
    `

    document.getElementById("tickets").prepend(div)
}


function closeTicket(id){

    fetch("/api/request/" + id,{
        method:"DELETE"
    })
}


function showNotification(text){

    if(Notification.permission === "granted"){

        new Notification("Новая заявка", {
            body: text
        })
    }
}


if(Notification.permission !== "granted"){
    Notification.requestPermission()
}