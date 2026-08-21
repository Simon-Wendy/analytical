import code.dataIntegration as ditn
import code.modelEnsembel as eml

def go():
    data = ditn.dataPipeline().getData()
    eml.modelEnsembel().go(data)

if __name__ == '__main__':
    go()