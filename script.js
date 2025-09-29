document.addEventListener("DOMContentLoaded", ()=>{

    const formInput = document.querySelector("form");
    const textArea = document.querySelector("textarea");
    const chat = document.querySelector(".chat");
    chatStory = [];
    let textInput = "";
    let hhmmTimestamp;

    getTime = () =>{
        const now = new Date();

        const hours = now.getHours();
        const minutes = now.getMinutes();

        const formattedHours = String(hours).padStart(2, '0');
        const formattedMinutes = String(minutes).padStart(2, '0');

        hhmmTimestamp = `${formattedHours}:${formattedMinutes}`;
    }

    addMessage = (whoIs, content, time) =>{

        messageTemplate = `
            <div class="message ${whoIs}">
                <div>${content}</div>
                <div class="timestamp ${whoIs}">${time}</div>
                ${whoIs == "user" ?
                    `<button class="redact ${whoIs}"></button>`: ''
                }
            </div>
        `

        chatStory.push(messageTemplate);
        chat.innerHTML = chatStory;
    }

    textArea.addEventListener("change", (e)=>{
        textInput = textArea.value;
    })

    formInput.addEventListener("submit", (e)=> {
        e.preventDefault();
        getTime();
        addMessage("user", textInput, hhmmTimestamp);
        addMessage("bot", textInput, hhmmTimestamp);
        chat.scrollTo(0, document.body.scrollHeight);
    })
    

})