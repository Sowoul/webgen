from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
import json

app = Flask(__name__)
app.config["SECRET_KEY"]="IDK123"

class Website:
    title = "Website"
    titlebar_color = "black"
    title_text_color = "white"
    footer_text = "footer"
    items = []



    def savefile(self):
        website_file = open('website.json','w')
        data_file = open('data.json','w')
        temp = {}
        for attr in ["title", "titlebar_color", "title_text_color" , "footer_text"]:
            temp[attr] = getattr(self,attr)
        json.dump(temp, website_file)
        json.dump(self.items , data_file)

website = Website()

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/store',methods = ["POST"])
def generate():
    if not (data := request.json):
        flash("Invalid data")
        return jsonify({"status" : "failure"}),404
    print(data)
    if data.get("type")!='items':
        for attr, value in data.items():
            setattr(website,attr,value)
        website.savefile()
        return jsonify({"status" : "success"}),202

    website.items.append(
        {
            "name" : data.get("value")[0],
            "price" : data.get("value")[1],
            "thumbnail" : data.get("value")[2]
        }
    )
    website.savefile()
    return jsonify({"status" : "success"}),202

if __name__ == '__main__':
    app.run(port = 8080, debug = True)
