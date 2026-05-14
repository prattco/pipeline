# main.py

from website import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
    
    # app.run(host='172.16.5.250',debug=True)
