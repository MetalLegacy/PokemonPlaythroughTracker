/*
 *
 * MAIN PAGE FUNCTIONALITY
 *
*/

const visitedPages = []

const fullRow = document.createElement("full-row")
fullRow.classList.add("row")

/*
 * EVENT LISTENERS
*/

// creates custom html elements
document.querySelector("#custom-elements").content.cloneNode(true).querySelectorAll("template").forEach(customElementTemplate => {
    customElements.define(
        customElementTemplate.id,
        class extends HTMLElement {
            constructor() {
                super()
                this.appendChild(customElementTemplate.content.cloneNode(true))
            }
        }
    )
})

// handels opening and closing dropdowns
function closeOpenDropdown(event) {
    try {
        let dropdown = document.querySelector(".dropdown[open]")
        if (dropdown.matches(".mon-select")) {
            try {
                dropdown.querySelectorAll(".item-group").forEach(group => group.classList.add("hide"))
            } catch (e) { }
        }
        dropdown.close()
        event.target.focus()
    } catch (e) { }
}

// attempts to close the open dropdown anytime an action happens outside a dropdown
document.addEventListener("click", event => { closeOpenDropdown(event) })
document.addEventListener("keydown", event => {
    if (!event.target.closest(".dropdown[open]") && event.key != "Tab") {
        closeOpenDropdown(event)
    }
})

// handles all clicks within the page
document.addEventListener("click", async event => {
    let button = event.target.closest("button")

    if (event.target.closest(".dropdown")) {
        processDropdownClick(event, button)
    }

    if (!button) {
        return
    }

    switch (button.getAttribute("aria-label")) {
        case "open dropdown": {
            event.stopPropagation()

            let dropdown = button.parentElement.querySelector(".dropdown")
            let wasOpen = dropdown.open
            closeOpenDropdown()

            if (!wasOpen) {
                try {
                    dropdown.querySelector(".item-group:first-child").classList.remove("hide")
                } catch (e) { }

                try {
                    clearDropdownSearch(dropdown)
                } catch (e) { }

                dropdown.show()

                try {
                    dropdown.querySelector(".scroll-wrapper").scrollTop = 0;
                } catch (e) { }

                dropdown.scrollIntoView({ behavior: "smooth", block: "end" })
            }
            break
        }
        case "open modal": {
            event.stopPropagation()
            closeOpenDropdown()
            button.parentElement.querySelector(".dropdown").showModal()
            break
        }
        case "remove mon": {
            button.closest(".selection").classList.add("unselected")
            calculateAllStats()
            break
        }
        case "add row": {
            await addNewRow()
            event.stopPropagation()
            break
        }
        case "move row up": {
            let currentRow = button.closest("full-row")
            currentRow.previousElementSibling.before(currentRow)
            saveRowIndices()
            break
        }
        case "remove row": {
            let row = button.closest("full-row")
            deleteRow(row.id)
            row.remove()
            saveRowIndices()
            break
        }
        case "move row down": {
            let currentRow = button.closest("full-row")
            currentRow.nextElementSibling.after(currentRow)
            saveRowIndices()
            break
        }
    }
}, true)

// handles all button clicks within a .dropdown
function processDropdownClick(event, button) {
    if (!button) {
        // pseudo elements can't be accessed by JS, so I can't quickly check if the ::backdrop was what was clicked
        if (clickWithinDropdown(event)) {
            event.stopPropagation()
        }
        return
    }

    if (button.closest("header")) processHeaderDropdownButtonClick(event, button)

    switch (button.getAttribute("aria-label")) {
        case "select item": {
            let oldItemGroup = button.closest(".item-group")
            oldItemGroup.classList.add("hide")
            oldItemGroup.querySelectorAll(".item").forEach(item => {
                item.classList.add("hide")
            })

            let scrollWrapper = button.closest(".scroll-wrapper")

            let newItemGroup = scrollWrapper.querySelector("#" + button.dataset.name.replaceAll(" ", "-"))

            if (newItemGroup) {
                newItemGroup.classList.remove("hide")
                clearDropdownSearch(button.closest(".dropdown"))
                visitedPages.push(oldItemGroup.id)
                event.stopPropagation()
                break
            }

            let selection = button.closest(".selection")
            for (const key in selection.dataset) {
                delete selection.dataset[key]
            }
            let dataset = button.dataset
            selection.style.setProperty("--img-src", "url(" + button.firstElementChild.src + ")")
            try {
                selection.style.setProperty("--shiny-img-src", "url(" + dataset.shiny + ")")
            } catch (e) { }

            for (const key in dataset) {
                selection.dataset[key] = dataset[key]
            }

            selection.classList.remove("unselected")

            id = selection.closest("full-row").id
            if (selection.matches("team-member")) {
                selection.querySelector(".nickname").placeholder = dataset.species
                saveMon(selection)
            } else {
                saveValue(id, "game", button.dataset["name"])
            }

            calculateAllStats()

            break
        }
        case "clear search": {
            clearDropdownSearch(button.closest(".dropdown"))
            break
        }
        case "back": {
            let scrollWrapper = button.closest(".selection").querySelector(".scroll-wrapper")

            let oldItemGroup = scrollWrapper.querySelector(".item-group:not(.hide)")
            oldItemGroup.classList.add("hide")

            let newItemGroup = scrollWrapper.querySelector("#" + visitedPages.pop())
            newItemGroup.classList.remove("hide")

            clearDropdownSearch(button.closest(".dropdown"))

            event.stopPropagation()
            break
        }
    }
}

// handles all buttons within the header dropdowns
function processHeaderDropdownButtonClick(event, button) {
    const body = document.querySelector("body")

    switch (button.getAttribute("aria-label")) {
        case "light theme": {
            body.classList.remove("dark")
            body.classList.add("light")
            saveSetting("theme", "light")
            break
        }
        case "dark theme": {
            body.classList.remove("light")
            body.classList.add("dark")
            saveSetting("theme", "dark")
            break
        }
        case "system theme": {
            body.classList.remove("dark")
            body.classList.remove("light")
            saveSetting("theme", "system")
            break
        }
        case "download save": {
            downloadSaveData()
            break
        }
        case "import save": {
            if (window.confirm("THIS CANNOT BE UNDONE.\nAre you sure you'd like to overwrite all current data?")) {
                document.querySelector("#import-save").click()
            } else {
                event.stopPropagation()
            }
            break
        }
        case "delete save": {
            if (window.confirm("THIS CANNOT BE UNDONE.\nAre you sure you'd like to delete all current data?")) {
                clearSaveData()
                location.reload()
            } else {
                event.stopPropagation()
            }
            break
        }
    }
}

// handles all text and checkbox input
document.addEventListener("input", event => {
    let target = event.target

    switch (target.id) {
        case "search-input": {
            filterDropdownItems(target)
            break
        }
        case "nickname":
        case "notes": {
            saveMon(target.closest("team-member"))
            break
        }
        case "time": {
            saveValue(target.closest("full-row").id, target.id, calculateTotalTime(target))
            break
        }
        case "include-boxed": {
            calculateAllStats()
            saveSetting("boxed", target.checked)
            break
        }
        case "show-review-columns": {
            saveSetting("expanded", target.checked)
            break
        }
        case "shiny-toggle": {
            saveMon(target.closest("team-member"))
            break
        }
        default: {
            saveValue(target.closest("full-row").id, target.id, target.innerHTML)
            break
        }
    }
})

// prevents #download-link from causing an endless loop
document.querySelector("#download-link").addEventListener("click", event => {
    event.stopPropagation()
})

// handles events to import save data
document.querySelector("#import-save").addEventListener("change", event => {
    importSaveData(event.target.files[0])
    location.reload()
})

/*
 * EVENT LISTENER CALLED FUNCTIONS
*/

// adds new row on the page
async function addNewRow(id, saveRow = true) {
    let newRow = fullRow.cloneNode()

    let tableBody = document.querySelector("#table-body")
    tableBody.appendChild(newRow)

    newId = id
    if (!newId) {
        let idNumber = await getSetting("numRowsCreated")
        newId = "row-" + ++idNumber
        newRow.querySelector("#game-select-button").click()
        saveSetting("numRowsCreated", idNumber)
        saveRowIndices()
    }

    newRow.id = newId

    if (saveRow) {
        saveNewRow(newId, tableBody.querySelectorAll("full-row").length - 1)
    }

    return newRow
}

// handles filtering dropdown items
function filterDropdownItems(searchBox) {
    let itemGroups = searchBox.closest(".dropdown").querySelectorAll(".item-group:not(.hide)")
    let searchValue = searchBox.value;

    itemGroups.forEach(itemGroup => {
        itemGroup.querySelectorAll(".item").forEach(item => {
            fuzzyCompare(item.dataset.name, searchValue) ? item.classList.remove("hide") : item.classList.add("hide")
        })
    })
}

// compares the closeness of two strings, returning true if they are close
function fuzzyCompare(name, searchInput) {
    // if the inputted value is noticeably longer than this String, it is highly likely this is not the match the user is looking for
    // threshold is based on what "felt good" during testing
    const tooLongThreshold = 1.5
    if (searchInput.length >= name.length * tooLongThreshold) return false

    // determining the longer and shorter of the two strings avoids index out of bounds exceptions during the actual comparison
    let longer =
        name.length >= searchInput.length ? name.toLowerCase() : searchInput.toLowerCase()
    let shorter =
        longer === name.toLowerCase() ? searchInput.toLowerCase() : name.toLowerCase()

    // any comparison where the shorter string is itself a substring of the longer string is kept as a match
    if (longer.indexOf(shorter) >= 0) return true

    const shorterLen = shorter.length
    const tooManyDifferencesThreshold = 0.25
    // compares all substrings of longer where length == shorterLen
    // if distance <= tooManyDifferencesThreshold% of shorterLen, return true
    for (let i = 0, j = shorterLen; i <= longer.length - shorterLen; i++, j++) {
        let distance = levenshtein(longer.substring(i, j), shorter)
        if (distance <= shorterLen * tooManyDifferencesThreshold) {
            return true
        }
    }

    return false
}

// returns the closeness of two strings
function levenshtein(a, b) {
    const tmp = [];
    let i, j, alen = a.length, blen = b.length, res;

    if (alen === 0) { return blen; }
    if (blen === 0) { return alen; }

    for (i = 0; i <= alen; i++) {
        tmp[i] = [i];
    }

    for (j = 0; j <= blen; j++) {
        tmp[0][j] = j;
    }

    for (i = 1; i <= alen; i++) {
        for (j = 1; j <= blen; j++) {
            res = (a[i - 1] === b[j - 1]) ? 0 : 1;
            tmp[i][j] = Math.min(
                tmp[i - 1][j] + 1,    // deletion
                tmp[i][j - 1] + 1,    // insertion
                tmp[i - 1][j - 1] + res // substitution
            );
        }
    }

    return tmp[alen][blen];
}

// used to check whether ot not the ::backdrop was clicked on
function clickWithinDropdown(event) {
    // if the dropdown is open modally, a manual check is needed to see if ::backdrop was clicked or not
    if (event.target.closest(".dropdown").matches(":modal")) {
        let boundingRect = event.target.getBoundingClientRect()
        let x = event.clientX, y = event.clientY

        if (x < boundingRect.left || x > boundingRect.right) {
            return false
        }

        if (y < boundingRect.top || y > boundingRect.bottom) {
            return false
        }

        return true
    }

    return true
}

// clears the searchbox and unhides all items
function clearDropdownSearch(dropdown) {
    let searchBox = dropdown.querySelector("#search-input")
    searchBox.value = ""
    filterDropdownItems(searchBox)
    event.stopPropagation()
}

/*
 * STATS
*/
// calculates the total time and displays it in the heading
// returns the value of target if it matches the pattern, otherwise returns null
function calculateTotalTime(target) {
    let hours = 0, minutes = 0, output = null

    document.querySelectorAll("#time:not(:user-invalid)").forEach(time => {
        let value = time.value

        if (!value.match(time.pattern)) {
            return
        }

        if (time === target) {
            output = value
        }

        values = value.split(":")

        hours += Number(values[0])
        minutes += Number(values[1])
    })

    document.querySelector("#total-time").textContent = Math.floor(hours + (minutes / 60)) + ":" + String(minutes % 60).padStart(2, "0")

    return output
}

// calculates all stat values and updates them accordingly
function calculateAllStats() {
    // resets current stat counts to 0
    document.querySelectorAll("#stats .count").forEach(count => {
        count.textContent = "0"
    })

    // keep track of base stats
    let numMons = 0
    let stats = { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0, bst: 0 }

    // determines whether or not boxed team-members are included
    let query = "team-member:not(.unselected)"
    if (!document.querySelector("#include-boxed").checked) {
        query = ".team " + query
    }

    // gather all the info from all the selected mons, assigns all except base stats
    document.querySelectorAll(query).forEach(mon => {
        let genStat = document.querySelector("#gen-" + mon.dataset.gen + " .count")
        genStat.innerHTML = Number(genStat.innerHTML) + 1

        let typeAStat = document.querySelector("#" + mon.dataset.typeA + " .count")
        typeAStat.innerHTML = Number(typeAStat.innerHTML) + 1

        try {
            let typeBStat = document.querySelector("#" + mon.dataset.typeB + " .count")
            typeBStat.innerHTML = Number(typeBStat.innerHTML) + 1
        } catch (e) { }

        if (mon.querySelector("#shiny-toggle").checked) {
            let shinyStat = document.querySelector("#shiny .count")
            shinyStat.innerHTML = Number(shinyStat.innerHTML) + 1
        }

        if (mon.dataset.mega) {
            let megaStat = document.querySelector("#mega .count")
            megaStat.innerHTML = Number(megaStat.innerHTML) + 1
        }

        if (mon.dataset.gmax) {
            let gmaxStat = document.querySelector("#gmax .count")
            gmaxStat.innerHTML = Number(gmaxStat.innerHTML) + 1
        }

        numMons++
        stats.hp += Number(mon.dataset.hp)
        stats.atk += Number(mon.dataset.atk)
        stats.def += Number(mon.dataset.def)
        stats.spa += Number(mon.dataset.spa)
        stats.spd += Number(mon.dataset.spd)
        stats.spe += Number(mon.dataset.spe)
        stats.bst += Number(mon.dataset.bst)
    })

    // calculates and assigns base stats
    for (let stat in stats) {
        let value = Math.round(stats[stat] / Math.max(numMons, 1))
        let element = document.querySelector("#" + stat)
        element.style.setProperty("--value", value)
        element.querySelector(".count").textContent = String(value)
        element.style.setProperty("--color", getBaseStatColor(value))
    }
}

// returns the color the base stat bar should be based on the value
function getBaseStatColor(value) {
    if (value == 0) {
        return null
    }
    if (value < 30) {
        return "#f34444"
    }
    if (value < 60) {
        return "#ff7f0f"
    }
    if (value < 90) {
        return "#ffdd57"
    }
    if (value < 120) {
        return "#a0e515"
    }
    if (value < 150) {
        return "#23cd5e"
    }
    return "#5ae0d9"
}

/*
 *
 * SAVING AND LOADING
 *
*/
const db = new Dexie("SaveData")

db.version(1).stores({
    settings: "&id, numRowsCreated, theme, expanded, boxed",
    rows: "&id, index"
})

db.open()

function saveValue(id, key, value) {
    if (value === null || String(value).trim() === "") {
        deleteValue(id, key)
        return
    }

    db.rows.update(id, { [key]: value })
}

function deleteValue(id, key) {
    const keys = key.split(".")
    db.rows.get(id).then(data => {
        let currentObj = data

        for (let currentKey of keys) {
            if (currentObj === undefined) return

            if (currentKey === keys.at(-1)) {
                delete currentObj[currentKey]

                if (Object.keys(currentObj).length === 0) {
                    deleteValue(id, keys.slice(0, -1).join("."))
                }

                break
            }
            currentObj = currentObj[currentKey]
        }

        db.rows.put(data)
    })
}

function saveSetting(key, value) {
    db.settings.update(1, { [key]: value })
}

function getSetting(key) {
    return db.settings.get(1).then(value => { return value[key] })
}

function saveNewRow(id, index) {
    db.rows.add({ id: id, index: index })
}

function deleteRow(id) {
    db.rows.delete(id)
}

function saveMon(teamMember) {
    let data = teamMember.matches(".unselected") ? null : {
        nickname: teamMember.querySelector("#nickname").value,
        species: teamMember.dataset.species,
        name: teamMember.dataset.name,
        shiny: teamMember.querySelector("#shiny-toggle").checked,
        notes: teamMember.querySelector("#notes").innerHTML
    }

    saveValue(teamMember.closest("full-row").id, teamMember.id, data)
}

function saveRowIndices() {
    let rows = document.querySelectorAll("full-row")
    for (let i = 0; i < rows.length; i++) {
        let row = rows[i]
        saveValue(row.id, "index", i)
    }
}

function downloadSaveData() {
    exportToJsonString(db.backendDB(), function (e, jsonString) {
        let link = document.querySelector("#download-link")
        let now = new Date()
        link.setAttribute("download", "")
        link.setAttribute("download", "PPT_Save_" + String(now.getDate()).padStart(2, "0") + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + now.getFullYear() + "_" + String(now.getHours()).padStart(2, "0") + "-" + String(now.getMinutes()).padStart(2, "0") + "-" + String(now.getSeconds()).padStart(2, "0") + ".json")
        link.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(jsonString));
        link.click()
    })
}

function clearSaveData() {
    clearDatabase(db.backendDB(), function (e) { })
}

function importSaveData(file) {
    let reader = new FileReader()

    reader.onload = file => {
        let text = file.target.result

        clearSaveData()

        importFromJsonString(db.backendDB(), text, function (e) { })
    }

    reader.readAsText(file)
}

async function loadData() {
    db.rows.orderBy("index").toArray().then(async rows => {
        console.log(rows)
        // if the save data is empty, initialize starting data
        if (!rows || rows.length === 0) {
            db.settings.put({ id: 1, numRowsCreated: 0, theme: "system", expanded: false, boxed: false })
            await addNewRow()
            return
        }

        // load settings
        document.querySelector("#include-boxed").checked = await getSetting("boxed")
        document.querySelector("#show-review-columns").checked = await getSetting("expanded")
        document.querySelector("body").classList.add(await getSetting("theme"))

        // load existing data
        for (let rowData of rows) {
            const rowElement = await addNewRow(rowData.id, false)

            for (let key in rowData) {
                const cell = rowElement.querySelector("#" + key)
                if (!cell) {
                    continue
                }

                let data = rowData[key]

                switch (cell.tagName) {
                    case "SPAN": {
                        if (key === "game") {
                            cell.querySelector('[data-name="' + data + '"]').click()
                            break
                        }
                        cell.innerHTML = data
                        break
                    }
                    case "INPUT": {
                        cell.value = data
                        break
                    }
                    case "TEAM-MEMBER": {
                        cell.querySelector('[data-species="' + data.species + '"][data-name="' + data.name + '"]').click()
                        cell.querySelector("#nickname").value = data.nickname
                        cell.querySelector("#shiny-toggle").checked = data.shiny
                        cell.querySelector("#notes").innerHTML = data.notes
                        break
                    }
                }
            }
        }
    })
}

loadData()