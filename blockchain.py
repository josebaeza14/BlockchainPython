import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request

import requests
from urllib.parse import urlparse


class  Blockchain():
    def  __init__(self):
        self.cadena_bloques = []
        self.transacciones = []
        self.nodos = set()
        """Esta es una forma económica de garantizar que la adición de nuevos
        nodos sea idempotente, lo que significa que no importa
        cuántas veces agreguemos un nodo específico, aparece exactamente una vez.
        """
        
        # Creamos el bloque genesis (Primer bloque sin predecesores)
        self.nuevo_bloque(1, anterior_hash=1)


    def registrar_nodo(self, direccion):
        """
        Agregue un nuevo nodo a la lista de nodos
        : direccion =  P.ej. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(direccion)
        self.nodos.add(parsed_url.netloc) #path


    def validar_cadena(self, cadena):
        """
        El primer método valid_chain()es responsable de verificar si una cadena
        es válida al recorrer cada bloque y verificar tanto el hash como la prueba.
        """        
        """
        Determinar si una cadena de bloques dada es válida
        : cadena param: <list> A blockchain
        : return: <bool> True si es válido, False si no
        """

        last_bloque = cadena[0]
        current_index = 1
        while current_index < len(cadena):
            bloque = cadena[current_index]
            print(f'{last_bloque}')
            print(f'{bloque}')
            print("\n-----------\n")
            # Verifica que el hash del bloque sea correcto
            if bloque['anterior_hash'] != self.hash(last_bloque):
                return False

            # Verifica que la Prueba de trabajo sea correcta
            if not self.valid_proof(last_bloque['prueba'], bloque['prueba']):
                return False

            last_bloque = bloque
            current_index += 1

        return True

    def resolver_conflictos(self):
        """
        resolve_conflicts()es un método que recorre todos los nodos
        vecinos, descarga sus cadenas y las verifica utilizando el método
        anterior. Si se encuentra una cadena
        válida, cuya longitud es mayor que la nuestra, reemplazamos la nuestra."""

        neighbours = self.nodos
        nueva_cadena = None

        # Solo estamos buscando cadenas más largas que las nuestras
        max_length = len(self.cadena_bloques)

        new_chain=None
        # Coge y verifica las cadenas de todos los nodos de nuestra red
        for node in neighbours:
            response = requests.get(f'http://{node}/cadena')

            if response.status_code == 200:
                print('JSON: '+str(response.json()))
                length = response.json()['longitud']
                chain = response.json()['cadena']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.validar_cadena(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.cadena_bloques = new_chain
            return True

        return False


    def proof_of_work(self, anterior_prueba):
        """
        Algoritmo de prueba de trabajo simple:
         - Encontrar un numero p tal que hash(p,p') contiene 4 ceros a la izquierda,
         donde p es el anterior de p'
         - p es el anterior prueba, y p' es el nuevo prueba
        """

        prueba_nueva = 0
        while self.valid_proof(anterior_prueba, prueba_nueva) == False:
            prueba_nueva += 1

        return prueba_nueva

    @staticmethod
    def valid_proof(anterior_prueba, prueba_nuevo):
        """
        Valida la prueba: ¿El hash (anterior_prueba, prueba_nuevo) contiene 4 ceros a la izquierda?
        : param anterior_prueba: <int> Prueba anterior
        : prueba de param: <int> Prueba actual
        : return: <bool> Verdadero si es correcto, falso si no.
        """

        guess = f'{anterior_prueba}{prueba_nuevo}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
        """Para ajustar la dificultad del algoritmo, podríamos modificar el número
        de ceros a la izquierda. Pero 4 es suficiente. Descubrirá que la adición
        de un cero inicial único marca una gran diferencia con el tiempo
        requerido para encontrar una solución."""
        
        
    def nuevo_bloque(self,prueba, anterior_hash=None):
        #Crea un nuevo bloque y lo agrega a la cadena
        """prueba -> Prueba dada por el algoritmo Proof of Work
        anterior_hash -> hash del bloque anterior
        return el nuevo bloque (DICCIONARIO)"""
        bloque = {
            'indice': len(self.cadena_bloques) + 1,
            'timestamp': time(),
            'transacciones': self.transacciones,
            'prueba': prueba,
            'anterior_hash': anterior_hash or self.hash(self.cadena_bloques[-1]),
        }

        # Reseteamos la lista de transacciones
        self.transacciones = []

        self.cadena_bloques.append(bloque)
        return bloque
        
        
    
    def nueva_transaccion(self, remitente, destinatario, cantidad):
        # Agrega una nueva transaccion a la lista de transacciones
        self.transacciones.append ({
            'remitente' : remitente,
            'destinatario' : destinatario,
            'cantidad' : cantidad,
        })

        return  self.ultimo_bloque['indice'] + 1
    
    @staticmethod
    def hash(bloque):
        """
        Crea un SHA-256 hash de un bloque
        SHA-256 es un algoritmo 
        """
        #Debemos asegurarnos de que el Diccionario esté Ordenado, o tendremos problemas de inconsistencia.
        bloque_string = json.dumps(bloque, sort_keys=True).encode()
        return hashlib.sha256(bloque_string).hexdigest()

    @property
    def ultimo_bloque(self):
        # Devuelve el último bloque en la cadena
        return self.cadena_bloques[-1]



# Instanciamos nuestro nodo
app = Flask(__name__)

# Genera una dirección global única para este nodo
node_identifier = str(uuid4()).replace('-', '')

# Instanciamos la blockchain
blockchain = Blockchain()


@app.route('/minar', methods=['GET'])
def minar():
    """
    Para que una transaccion se incluya en el libro mayor, es decir,
    sea validada, un minero
    debe aceptarlo, minando
    """
    """
    SOLO PUEDEN MINAR LOS MINEROS,NO CUALQUIERA
    """
    # Ejecutamos el algoritmo de prueba de trabajo para obtener la siguiente prueba ...
    last_block = blockchain.ultimo_bloque
    last_proof = last_block['prueba']
    proof = blockchain.proof_of_work(last_proof)

    # Debemos recibir una recompensa por encontrar la prueba.
    # El remitente es "0" para indicar que este nodo ha extraído una nueva moneda.
    blockchain.nueva_transaccion(
        remitente="0",
        destinatario="josejosejosejosejosejose", #Ese va a ser mi nodo
        cantidad=1,
    )

    # Forge el nuevo bloque agregándolo a la cadena
    previous_hash = blockchain.hash(last_block)
    block = blockchain.nuevo_bloque(proof, previous_hash)

    response = {
        'message': "Nuevo Bloque Unido",
        'indice': block['indice'],
        'transacciones': block['transacciones'],
        'prueba': block['prueba'],
        'anterior_hash': block['anterior_hash'],
    }
    return jsonify(response), 200

  
@app.route('/transaccion/nueva', methods=['POST'])
def nueva_transaccion():
    """
    {
    "remitente": "1010",
    "destinatario": "joselito",
    "cantidad": 3
    }
    """
    values = request.get_json()
    print('Valores: '+str(values))

    # Check that the required fields are in the POST'ed data
    required = ['remitente', 'destinatario', 'cantidad']
    if not all(k in values for k in required):
        return 'Faltan Valores!', 400

    # Create a new Transaction
    index = blockchain.nueva_transaccion(values['remitente'], values['destinatario'], values['cantidad'])

    response = {'message': f'La Transaccion se agregara al bloque {index}'}
    return jsonify(response), 201


@app.route('/cadena', methods=['GET'])
def Cadena_Total():
    response = {
        'cadena': blockchain.cadena_bloques,
        'longitud': len(blockchain.cadena_bloques),
    }
    return jsonify(response), 200


@app.route('/nodos/registrar', methods=['POST'])
def registrar_nodos():
    # {"nodos": "http://192.168.0.119:5000"}
    values = request.get_json()

    nodes = values.get('nodos')
    if nodes is None:
        return "Error: Por favor, ponga una lista correcta de nodos", 400

    blockchain.registrar_nodo(nodes)

    response = {
        'message': 'El nuevo nodo ha sido añadido!',
        'Nodos_Totales': list(blockchain.nodos),
    }
    return jsonify(response), 201


@app.route('/nodos/resolver', methods=['GET'])
def consenso():
    replaced = blockchain.resolver_conflictos()

    if replaced:
        response = {
            'message': 'Nuestra cadena fue reemplazada',
            'new_chain': blockchain.cadena_bloques
        }
    else:
        response = {
            'message': 'Nuestra cadena tiene autoridad',
            'chain': blockchain.cadena_bloques
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
