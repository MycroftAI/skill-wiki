import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Item {
    id: imgOuterContainer
    property alias imgSrc: img.source

    Item {
        id: imgInnerContainer
        width: parent.width
        height: parent.height
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom

        Image {
            id: img
            anchors.fill: parent
            opacity: 0
            fillMode: Image.PreserveAspectFit

            asynchronous: true
            onStatusChanged: {
                if (status == Image.Ready) {
                    opacity = 1
                }
            }
        }
    }

    Mycroft.BusyIndicator {
        anchors.centerIn: parent
        running: img.status === Image.Loading || img.source == "" ? 1 : 0
        visible: running
    }
}
