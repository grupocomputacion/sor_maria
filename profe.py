import sqlite3

def parche_db():
    conn = sqlite3.connect('gestion_alumnos.db')
    c = conn.cursor()
    try:
        # Agregamos la columna 'profesor' a la tabla existente
        c.execute("ALTER TABLE alumnos ADD COLUMN profesor TEXT")
        conn.commit()
        print("Columna 'profesor' agregada con éxito.")
    except sqlite3.OperationalError:
        print("La columna ya existe o hubo un error.")
    finally:
        conn.close()

if __name__ == "__main__":
    parche_db()
