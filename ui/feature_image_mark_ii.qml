import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    cardBackgroundOverlayColor: "black"

    Title {
            id: articleTitle
            anchors.top: parent.top
            fontSize: 47
            fontStyle: "Bold"
            heightUnits: 3
            text: sessionData.title
        }

    Rectangle {
        id: featureImageContainer
        color: "black"
        radius: 16
        height: parent.height - gridUnit * 6
        width: parent.width
        anchors.top: articleTitle.bottom
        anchors.topMargin: gridUnit * 2
        anchors.bottomMargin: gridUnit

        Image {
            id: featureImage
            anchors.horizontalCenter: parent.horizontalCenter
            height: parent.height
            width: parent.width
            fillMode: Image.PreserveAspectFit
            source: sessionData.imgLink
        }
        Mycroft.BusyIndicator {
            anchors.centerIn: parent
            visible: sessionData.imgLink == ''
            running: True
        }
    }
}
