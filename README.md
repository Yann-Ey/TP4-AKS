# Compte-rendu TP - Module 10 : Déploiement sur Azure Kubernetes Service (AKS)


-----

## 1\. Objectifs du TP

L'objectif de ce laboratoire était de maîtriser le cycle de vie complet d'une application sur le cloud Azure :

  * Provisionner un cluster managé (**AKS**).
  * Créer un registre d'images privé (**ACR**).
  * Gérer la configuration (**ConfigMap**) et les secrets (**Secret**).
  * Mettre en place un stockage partagé (**PVC en mode RWX**).
  * Assurer la haute disponibilité et tester la résilience du système.

-----

## 2\. Mise en place de l'Infrastructure

Nous avons commencé par créer les ressources Azure via Azure CLI, en définissant un groupe de ressources et un cluster à 2 nœuds pour assurer la redondance.

### 2.1 Création des ressources

```powershell
# Création du groupe de ressources
az group create --name tp-aks-group --location francecentral

# Création du cluster AKS (2 nœuds)
az aks create --resource-group tp-aks-group --name monClusterAKS --node-count 2 --generate-ssh-keys
```

### 2.2 Connexion au cluster

Configuration de `kubectl` pour communiquer avec le cluster Azure :

```powershell
az aks get-credentials --resource-group tp-aks-group --name monClusterAKS --overwrite-existing
```

-----

## 3\. Configuration de l'environnement

Pour isoler l'application, nous avons créé un **Namespace** dédié et configuré les variables d'environnement (non-sensibles et sensibles).

  * **Namespace :** `tp-app`
  * **ConfigMap :** Message d'accueil et extension `.txt`.
  * **Secret :** Mot de passe d'upload (`btssio`).

<!-- end list -->

```powershell
kubectl create namespace tp-app
kubectl create configmap app-config --namespace tp-app --from-literal=APP_MESSAGE="Bienvenue sur mon Azure AKS !" --from-literal=UPLOAD_ALLOWED_EXT=".txt"
kubectl create secret generic app-secret --namespace tp-app --from-literal=UPLOAD_PASSWORD="btssio"
```

-----

## 4\. Conteneurisation et Registre (ACR)

Nous avons développé une API Python (Flask) et créé un `Dockerfile` pour la conteneuriser. Au lieu d'utiliser Docker localement, nous avons utilisé **ACR Tasks** pour construire l'image directement dans le cloud.

### 4.1 Création du Registre et Build

Nous avons créé un registre nommé **`acrtpyanne2025`** et l'avons lié au cluster AKS.

```powershell
# Création du registre
az acr create --resource-group tp-aks-group --name acrtpyanne2025 --sku Basic

# Liaison au cluster (Attach)
az aks update --resource-group tp-aks-group --name monClusterAKS --attach-acr acrtpyanne2025

# Build de l'image
az acr build --registry acrtpyanne2025 --image tp-app:v1 .
```

-----

## 5\. Stockage Persistant (RWX)

L'application nécessitant que plusieurs répliques accèdent aux mêmes fichiers, nous avons provisionné un volume **Azure Files** en mode **ReadWriteMany (RWX)**.

**Vérification du statut Bound :**

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl get pvc -n tp-app
NAME         STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
shared-pvc   Bound    pvc-ac3407a8-b633-4b77-89a9-363b9fc0f27f   1Gi        RWX            azurefile      <unset>                 4m10s
```

-----

## 6\. Déploiement et Exposition

### 6.1 Déploiement (Deployment)

Nous avons déployé 2 répliques de l'application utilisant l'image `acrtpyanne2025.azurecr.io/tp-app:v1`.

**Vérification des Pods :**

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl get pods -n tp-app
NAME                             READY   STATUS    RESTARTS   AGE
tp-app-deploy-766f684f69-69l47   1/1     Running   0          61s
tp-app-deploy-766f684f69-wbsjg   1/1     Running   0          61s
```

### 6.2 Exposition (Service)

Un Service de type **LoadBalancer** a été créé pour obtenir une IP publique.

**Obtention de l'IP Publique :**

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl get service -n tp-app
NAME             TYPE           CLUSTER-IP     EXTERNAL-IP     PORT(S)        AGE
tp-app-service   LoadBalancer   10.0.213.171   172.189.51.43   80:31109/TCP   49s
```

*Adresse IP d'accès : `172.189.51.43`*

-----

## 7\. Tests Fonctionnels

Nous avons testé l'API en simulant un client externe.

### 7.1 Test de sécurité (Mauvais mot de passe)

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> curl.exe -X POST -F "file=@test.txt" -F "password=mauvaispass" http://172.189.51.43/upload
{"error":"Mauvais mot de passe !"}
```

> Le Secret fonctionne : l'accès est refusé.

### 7.2 Test nominal (Bon mot de passe)

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> curl.exe -X POST -F "file=@test.txt" -F "password=btssio" http://172.189.51.43/upload
{"status":"Fichier sauvegard\u00e9 avec succ\u00e8s !"}
```

> L'upload fonctionne : le fichier est écrit sur le volume partagé.

*(Insérer ici tes captures d'écran du navigateur montrant le fichier test.txt)*

-----

## 8\. Tests Techniques : RWX et Résilience

### 8.1 Vérification du partage de fichiers (RWX)

Nous avons vérifié que le fichier uploadé est visible depuis les deux Pods distincts.

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl exec -n tp-app tp-app-deploy-766f684f69-69l47 -- ls /data
test.txt
PS C:\Users\yanne\Documents\tp-aks\app> kubectl exec -n tp-app tp-app-deploy-766f684f69-wbsjg -- ls /data
test.txt
```

**Conclusion :** Le volume est bien monté en lecture/écriture sur plusieurs nœuds simultanément.

### 8.2 Test de Haute Disponibilité (Chaos Monkey)

Nous avons supprimé manuellement un Pod pour vérifier l'auto-réparation.

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl delete pod tp-app-deploy-766f684f69-69l47 -n tp-app
pod "tp-app-deploy-766f684f69-69l47" deleted
```

**Résultat immédiat :** Kubernetes a recréé un nouveau Pod (`wsdct`) pour maintenir l'état désiré (2 répliques).

```powershell
PS C:\Users\yanne\Documents\tp-aks\app> kubectl get pods -n tp-app
NAME                             READY   STATUS    RESTARTS   AGE
tp-app-deploy-766f684f69-wbsjg   1/1     Running   0          17m
tp-app-deploy-766f684f69-wsdct   1/1     Running   0          53s
```





```powershell
az group delete --name tp-aks-group --yes --no-wait
```
